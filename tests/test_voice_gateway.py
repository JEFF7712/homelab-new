from __future__ import annotations

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).parents[1] / "gitops/voice/gateway/gateway.py"
SPEC = importlib.util.spec_from_file_location("voice_gateway", PATH)
assert SPEC and SPEC.loader
GATEWAY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GATEWAY
SPEC.loader.exec_module(GATEWAY)


class GatewayProtocolTest(unittest.TestCase):
    def test_event_round_trip(self) -> None:
        async def run() -> dict:
            reader = asyncio.StreamReader()
            event = {"type": "audio-chunk", "data": {"rate": 16000}, "payload": b"pcm"}
            reader.feed_data(GATEWAY.encode_event(event))
            reader.feed_eof()
            return await GATEWAY.read_event(reader)

        self.assertEqual(
            asyncio.run(run()),
            {"type": "audio-chunk", "data": {"rate": 16000}, "payload": b"pcm"},
        )

    def test_backend_order_is_preserved(self) -> None:
        backends = GATEWAY.parse_backends("primary=one:1,fallback=two:2")
        self.assertEqual(
            [backend.name for backend in backends], ["primary", "fallback"]
        )

    def test_stt_native_latency_metric(self) -> None:
        metrics = GATEWAY.Metrics("stt")
        turn = GATEWAY.TurnMetrics("stt", "nemotron", metrics)
        turn.client_event({"type": "audio-stop", "data": {}, "payload": b""})
        turn.backend_event({"type": "transcript", "data": {}, "payload": b""})
        rendered = metrics.render([]).decode()
        self.assertIn("jarvis_stt_vad_to_final_seconds_count", rendered)

    def test_tts_native_metrics(self) -> None:
        metrics = GATEWAY.Metrics("tts")
        turn = GATEWAY.TurnMetrics("tts", "chatterbox", metrics)
        turn.client_event({"type": "synthesize", "data": {}, "payload": b""})
        turn.backend_event(
            {
                "type": "audio-start",
                "data": {"rate": 24000, "width": 2, "channels": 1},
                "payload": b"",
            }
        )
        turn.backend_event({"type": "audio-chunk", "data": {}, "payload": b"x" * 48000})
        turn.backend_event({"type": "audio-stop", "data": {}, "payload": b""})
        rendered = metrics.render([]).decode()
        self.assertIn("jarvis_tts_time_to_first_audio_seconds_count", rendered)
        self.assertIn("jarvis_tts_synthesis_realtime_factor_count", rendered)

    def test_tts_retries_piper_when_primary_fails_before_audio(self) -> None:
        async def run() -> tuple[list[dict], str]:
            async def failing(reader, writer):
                await GATEWAY.read_event(reader)
                writer.close()
                await writer.wait_closed()

            async def fallback(reader, writer):
                await GATEWAY.read_event(reader)
                writer.write(
                    GATEWAY.encode_event(
                        {
                            "type": "audio-start",
                            "data": {"rate": 1, "width": 2, "channels": 1},
                        }
                    )
                )
                writer.write(
                    GATEWAY.encode_event(
                        {
                            "type": "audio-chunk",
                            "data": {"rate": 1, "width": 2, "channels": 1},
                            "payload": b"ok",
                        }
                    )
                )
                writer.write(GATEWAY.encode_event({"type": "audio-stop", "data": {}}))
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            first = await asyncio.start_server(failing, "127.0.0.1", 0)
            second = await asyncio.start_server(fallback, "127.0.0.1", 0)
            metrics = GATEWAY.Metrics("tts")
            gateway = GATEWAY.Gateway(
                "tts",
                [
                    GATEWAY.Backend(
                        "chatterbox", "127.0.0.1", first.sockets[0].getsockname()[1]
                    ),
                    GATEWAY.Backend(
                        "piper", "127.0.0.1", second.sockets[0].getsockname()[1]
                    ),
                ],
                metrics,
                connect_timeout=0.2,
            )
            listener = await asyncio.start_server(gateway.handle, "127.0.0.1", 0)
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", listener.sockets[0].getsockname()[1]
            )
            writer.write(
                GATEWAY.encode_event({"type": "synthesize", "data": {"text": "Done."}})
            )
            await writer.drain()
            events = []
            while (event := await GATEWAY.read_event(reader)) is not None:
                events.append(event)
                if event["type"] == "audio-stop":
                    break
            rendered = metrics.render([]).decode()
            writer.close()
            await writer.wait_closed()
            listener.close()
            first.close()
            second.close()
            await listener.wait_closed()
            await first.wait_closed()
            await second.wait_closed()
            return events, rendered

        events, rendered = asyncio.run(run())
        self.assertEqual(
            [event["type"] for event in events],
            ["audio-start", "audio-chunk", "audio-stop"],
        )
        self.assertIn(
            'jarvis_gateway_fallbacks_total{backend="piper",mode="tts"} 1.0', rendered
        )

    def test_tts_does_not_splice_fallback_after_audio_started(self) -> None:
        async def run() -> tuple[list[dict], str]:
            async def partial(reader, writer):
                await GATEWAY.read_event(reader)
                fmt = {"rate": 1, "width": 2, "channels": 1}
                writer.write(GATEWAY.encode_event({"type": "audio-start", "data": fmt}))
                writer.write(
                    GATEWAY.encode_event(
                        {"type": "audio-chunk", "data": fmt, "payload": b"partial"}
                    )
                )
                await writer.drain()
                writer.close()
                await writer.wait_closed()

            fallback_called = False

            async def fallback(reader, writer):
                nonlocal fallback_called
                fallback_called = True
                writer.close()
                await writer.wait_closed()

            first = await asyncio.start_server(partial, "127.0.0.1", 0)
            second = await asyncio.start_server(fallback, "127.0.0.1", 0)
            metrics = GATEWAY.Metrics("tts")
            gateway = GATEWAY.Gateway(
                "tts",
                [
                    GATEWAY.Backend(
                        "chatterbox", "127.0.0.1", first.sockets[0].getsockname()[1]
                    ),
                    GATEWAY.Backend(
                        "piper", "127.0.0.1", second.sockets[0].getsockname()[1]
                    ),
                ],
                metrics,
                connect_timeout=0.2,
            )
            listener = await asyncio.start_server(gateway.handle, "127.0.0.1", 0)
            reader, writer = await asyncio.open_connection(
                "127.0.0.1", listener.sockets[0].getsockname()[1]
            )
            writer.write(
                GATEWAY.encode_event({"type": "synthesize", "data": {"text": "Done."}})
            )
            await writer.drain()
            events = []
            while (event := await GATEWAY.read_event(reader)) is not None:
                events.append(event)
            writer.close()
            await writer.wait_closed()
            listener.close()
            first.close()
            second.close()
            await listener.wait_closed()
            await first.wait_closed()
            await second.wait_closed()
            return events, rendered(metrics), fallback_called

        def rendered(metrics):
            return metrics.render([]).decode()

        events, metrics_text, fallback_called = asyncio.run(run())
        self.assertEqual(
            [event["type"] for event in events], ["audio-start", "audio-chunk"]
        )
        self.assertFalse(fallback_called)
        self.assertNotIn("jarvis_gateway_fallbacks_total", metrics_text)


if __name__ == "__main__":
    unittest.main()
