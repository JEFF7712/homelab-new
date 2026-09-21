"""Offline tests for the Chatterbox Turbo Wyoming TTS bridge.

Executes gitops/voice/chatterbox-bridge/server.py directly with a fake
synthesis engine, then drives TtsServer.handle_client over loopback TCP.
No GPU, model weights, or third-party Wyoming libraries required.
"""

from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = REPO_ROOT / "gitops" / "voice" / "chatterbox-bridge" / "server.py"


def load_server() -> types.ModuleType:
    code = SERVER_PATH.read_text()
    module = types.ModuleType("chatterbox_bridge_under_test")
    module.__file__ = str(SERVER_PATH)
    sys.modules[module.__name__] = module
    exec(compile(code, str(SERVER_PATH), "exec"), module.__dict__)
    return module


SERVER = load_server()


class FakeEngine:
    """Scripted synthesis engine: 0.1s of tone per character, 24 kHz."""

    RATE = 24000

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.texts: list[str] = []

    def synthesize(self, text: str) -> tuple[bytes, int]:
        self.texts.append(text)
        if self.fail:
            raise RuntimeError("boom-synth")
        frames = max(1, len(text) * self.RATE // 10)
        pcm = b"\x00\x10" * frames
        return pcm, self.RATE


def make_config(**overrides) -> object:
    config = SERVER.TtsConfig()
    for key, value in overrides.items():
        setattr(config, key, value)
    return config


def decode_frames(buf: bytes) -> list[dict]:
    """Minimal Wyoming frame decoder for assertions."""
    import json

    events: list[dict] = []
    while buf:
        line, sep, rest = buf.partition(b"\n")
        if not sep:
            break
        try:
            header = json.loads(line)
        except ValueError:
            break
        data_len = int(header.get("data_length") or 0)
        payload_len = int(header.get("payload_length") or 0)
        if len(rest) < data_len + payload_len:
            break
        data = json.loads(rest[:data_len]) if data_len else {}
        payload = rest[data_len : data_len + payload_len]
        events.append({"type": header.get("type"), "data": data, "payload": payload})
        buf = rest[data_len + payload_len :]
    return events


async def drive(script: list[tuple], engine: FakeEngine, config=None) -> bytes:
    """Serve handle_client on loopback, play script, return raw replies."""
    config = config or make_config()
    tts = SERVER.TtsServer(config, engine)
    got = bytearray()
    done = asyncio.Event()

    async def on_connect(reader, writer) -> None:
        try:
            await tts.handle_client(reader, writer)
        finally:
            done.set()

    server = await asyncio.start_server(on_connect, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    for kind, data, payload in script:
        writer.write(SERVER.encode_event(kind, data, payload or b""))
    await writer.drain()
    for _ in range(400):
        try:
            chunk = await asyncio.wait_for(reader.read(65536), timeout=0.05)
            if chunk:
                got += chunk
        except asyncio.TimeoutError:
            pass
        if b'"audio-stop"' in got:
            await asyncio.sleep(0.2)
            try:
                while True:
                    chunk = await asyncio.wait_for(reader.read(65536), timeout=0.2)
                    if not chunk:
                        break
                    got += chunk
            except asyncio.TimeoutError:
                pass
            break
    writer.close()
    await asyncio.wait_for(done.wait(), timeout=10)
    server.close()
    return bytes(got)


def synth_script(text: str, voice: str = "jarvis") -> list[tuple]:
    return [("synthesize", {"text": text, "voice": {"name": voice}}, b"")]


class TtsTurnTest(unittest.TestCase):
    def test_describe_advertises_jarvis_voice(self) -> None:
        engine = FakeEngine()
        raw = asyncio.run(drive([("describe", {}, b"")], engine))
        events = decode_frames(raw)
        infos = [e for e in events if e["type"] == "info"]
        self.assertEqual(len(infos), 1)
        programs = infos[0]["data"]["tts"]
        self.assertEqual(programs[0]["name"], "chatterbox-turbo")
        self.assertEqual(programs[0]["voices"][0]["name"], "jarvis")

    def test_full_turn_audio_shape(self) -> None:
        engine = FakeEngine()
        raw = asyncio.run(drive(synth_script("Done."), engine))
        events = decode_frames(raw)
        kinds = [e["type"] for e in events]
        self.assertEqual(kinds[0], "audio-start")
        self.assertEqual(kinds[-1], "audio-stop")
        self.assertGreaterEqual(kinds.count("audio-chunk"), 1)
        start = events[0]["data"]
        self.assertEqual(
            (start["rate"], start["width"], start["channels"]), (24000, 2, 1)
        )
        pcm = b"".join(e["payload"] for e in events if e["type"] == "audio-chunk")
        self.assertEqual(pcm, b"\x00\x10" * (len("Done.") * 2400))
        self.assertEqual(engine.texts, ["Done."])

    def test_chunk_size_honored(self) -> None:
        engine = FakeEngine()
        config = make_config(chunk_ms=100)
        raw = asyncio.run(drive(synth_script("Hello there."), engine, config))
        events = decode_frames(raw)
        chunks = [e["payload"] for e in events if e["type"] == "audio-chunk"]
        for piece in chunks[:-1]:
            self.assertEqual(len(piece), 24000 * 100 // 1000 * 2)

    def test_empty_text_sends_silence(self) -> None:
        engine = FakeEngine()
        raw = asyncio.run(drive(synth_script("   "), engine))
        events = decode_frames(raw)
        self.assertEqual([e["type"] for e in events], ["audio-start", "audio-stop"])
        self.assertEqual(engine.texts, [])

    def test_unknown_voice_falls_back(self) -> None:
        engine = FakeEngine()
        raw = asyncio.run(drive(synth_script("Done.", voice="alan"), engine))
        events = decode_frames(raw)
        self.assertEqual(events[-1]["type"], "audio-stop")
        self.assertGreaterEqual(sum(1 for e in events if e["type"] == "audio-chunk"), 1)
        self.assertEqual(engine.texts, ["Done."])

    def test_engine_failure_sends_silence_and_survives(self) -> None:
        engine = FakeEngine(fail=True)
        raw = asyncio.run(drive(synth_script("Done."), engine))
        events = decode_frames(raw)
        self.assertEqual([e["type"] for e in events], ["audio-start", "audio-stop"])
        engine.fail = False
        raw = asyncio.run(drive(synth_script("Done."), engine))
        events = decode_frames(raw)
        self.assertGreaterEqual(sum(1 for e in events if e["type"] == "audio-chunk"), 1)

    def test_streaming_events_buffered_into_one_turn(self) -> None:
        engine = FakeEngine()
        script = [
            ("synthesize-start", {"voice": {"name": "jarvis"}}, b""),
            ("synthesize-chunk", {"text": "Good "}, b""),
            ("synthesize-chunk", {"text": "morning."}, b""),
            ("synthesize-stop", {"voice": {"name": "jarvis"}}, b""),
        ]
        raw = asyncio.run(drive(script, engine))
        events = decode_frames(raw)
        self.assertEqual(events[-1]["type"], "audio-stop")
        self.assertEqual(engine.texts, ["Good morning."])


class TtsTextTest(unittest.TestCase):
    def test_tags_stripped_by_default(self) -> None:
        engine = FakeEngine()
        asyncio.run(drive(synth_script("[laugh] Done."), engine))
        self.assertEqual(engine.texts[-1], "Done.")

    def test_tags_kept_when_allowed(self) -> None:
        engine = FakeEngine()
        config = make_config(allow_tags=True)
        asyncio.run(drive(synth_script("[laugh] Done."), engine, config))
        self.assertEqual(engine.texts[-1], "[laugh] Done.")

    def test_samples_to_pcm16_values(self) -> None:
        pcm = SERVER.samples_to_pcm16([0.0, 1.0, -1.0, 2.0, -2.0])
        import struct

        self.assertEqual(struct.unpack("<5h", pcm), (0, 32767, -32767, 32767, -32768))

    def test_config_validation(self) -> None:
        bad = make_config(port=0)
        with self.assertRaises(ValueError):
            bad.validate()
        bad = make_config(device="mps")
        with self.assertRaises(ValueError):
            bad.validate()
        bad = make_config(chunk_ms=5)
        with self.assertRaises(ValueError):
            bad.validate()
        make_config().validate()

    def test_resolve_reference(self) -> None:
        resolve = SERVER.resolve_reference
        self.assertIsNone(resolve(""))
        self.assertIsNone(resolve("/nonexistent/jarvis.wav"))

    def test_watermark_passthrough_when_perth_broken(self) -> None:
        import sys
        import types

        stub = types.ModuleType("perth")
        stub.PerthImplicitWatermarker = None
        saved = sys.modules.get("perth")
        sys.modules["perth"] = stub
        try:
            SERVER.ensure_watermarker()
            wav = [0.1, 0.2]
            self.assertEqual(
                stub.PerthImplicitWatermarker().apply_watermark(wav, sample_rate=24000),
                wav,
            )
        finally:
            if saved is not None:
                sys.modules["perth"] = saved
            else:
                sys.modules.pop("perth", None)


if __name__ == "__main__":
    unittest.main()
