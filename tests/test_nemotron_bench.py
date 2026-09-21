"""Offline unit tests for the Nemotron benchmark harness."""

from __future__ import annotations

import asyncio
import unittest

from scripts.nemotron_bench import (
    TurnTimestamps,
    build_commit,
    build_session_update,
    build_speech_contexts,
    chunk_pcm,
    decode_wyoming_frame,
    encode_wyoming,
    entity_recall,
    normalize_text,
    parse_realtime_url,
    read_wyoming_event,
    score_turn,
    summarize,
    wer,
    ws_decode_frame,
    ws_encode_frame,
)


class TimingTest(unittest.TestCase):
    def test_metrics_split(self) -> None:
        stamps = TurnTimestamps(0.0, 5.0, 5.25, 5.27, 5.28)
        metrics = stamps.metrics()
        self.assertAlmostEqual(metrics["vad_latency"], 0.25)
        self.assertAlmostEqual(metrics["asr_finalization"], 0.02)
        self.assertAlmostEqual(metrics["proxy_overhead"], 0.01)
        self.assertAlmostEqual(metrics["stt_post_speech"], 0.03)
        self.assertAlmostEqual(metrics["voice_post_speech"], 0.28)

    def test_direct_backend_has_zero_proxy_overhead(self) -> None:
        stamps = TurnTimestamps(1.0, 2.0, 2.1, 2.12, 2.12)
        self.assertAlmostEqual(stamps.metrics()["proxy_overhead"], 0.0)


class WerTest(unittest.TestCase):
    def test_identical_is_zero(self) -> None:
        self.assertEqual(wer("Turn off the lights", "turn off the lights."), 0.0)

    def test_one_substitution(self) -> None:
        self.assertAlmostEqual(
            wer("turn on kitchen lights", "turn off kitchen lights"), 0.25
        )

    def test_empty_hypothesis(self) -> None:
        self.assertEqual(wer("hello world", ""), 1.0)

    def test_both_empty(self) -> None:
        self.assertEqual(wer("", ""), 0.0)

    def test_normalize(self) -> None:
        self.assertEqual(normalize_text("  Living Room! "), "living room")


class EntityRecallTest(unittest.TestCase):
    def test_recall(self) -> None:
        recall, details = entity_recall(
            ["Govee", "living room"], "Turn on the govee lights"
        )
        self.assertAlmostEqual(recall, 0.5)
        self.assertTrue(details["Govee"])
        self.assertFalse(details["living room"])

    def test_empty_entities(self) -> None:
        recall, details = entity_recall([], "anything")
        self.assertEqual(recall, 1.0)
        self.assertEqual(details, {})

    def test_score_turn_shape(self) -> None:
        result = score_turn("turn on govee lights", "turn on govee lights", ["Govee"])
        self.assertEqual(result["wer"], 0.0)
        self.assertEqual(result["entity_recall"], 1.0)
        self.assertEqual(result["n_ref_words"], 4)


class WyomingFramingTest(unittest.TestCase):
    def test_round_trip_with_payload(self) -> None:
        payload = b"\x00\x01" * 160
        frame = encode_wyoming(
            "audio-chunk", {"rate": 16000, "width": 2, "channels": 1}, payload
        )
        event, remaining = decode_wyoming_frame(frame)
        self.assertEqual(event["type"], "audio-chunk")
        data = event["data"]
        assert isinstance(data, dict)
        self.assertEqual(data["rate"], 16000)
        self.assertEqual(event["payload"], payload)
        self.assertEqual(remaining, b"")

    def test_round_trip_without_payload(self) -> None:
        frame = encode_wyoming("audio-stop")
        event, _ = decode_wyoming_frame(frame)
        self.assertEqual(event["type"], "audio-stop")

    def test_async_reader(self) -> None:
        async def run() -> dict[str, object] | None:
            frame = encode_wyoming("transcript", {"text": "hello"})
            reader = asyncio.StreamReader()
            reader.feed_data(frame)
            reader.feed_eof()
            return await read_wyoming_event(reader)

        event = asyncio.run(run())
        assert event is not None
        self.assertEqual(event["type"], "transcript")

    def test_incomplete_frame_raises(self) -> None:
        with self.assertRaises(ValueError):
            decode_wyoming_frame(b'{"type": "audio-stop"')

    def test_chunk_pcm_sizes(self) -> None:
        pcm = b"\x00\x01" * 16000  # 1s of 16kHz 16-bit mono
        chunks = chunk_pcm(pcm, 100)
        self.assertEqual(len(chunks), 10)
        self.assertTrue(all(len(c) == 3200 for c in chunks))

    def test_chunk_pcm_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            chunk_pcm(b"data", 0)


class SessionPayloadTest(unittest.TestCase):
    def test_endpointing_omitted_by_default(self) -> None:
        payload = build_session_update()
        session = payload["session"]
        assert isinstance(session, dict)
        self.assertNotIn("endpointing_ms", session)
        self.assertEqual(session["sample_rate"], 16000)
        self.assertEqual(session["language"], "en-US")

    def test_speech_contexts_shape(self) -> None:
        contexts = build_speech_contexts(["Govee", "living room"], boost=2.5)
        self.assertEqual(
            contexts, [{"phrases": ["Govee", "living room"], "boost": 2.5}]
        )
        payload = build_session_update(speech_contexts=contexts)
        session = payload["session"]
        assert isinstance(session, dict)
        self.assertEqual(session["speech_contexts"], contexts)

    def test_boost_range_enforced(self) -> None:
        with self.assertRaises(ValueError):
            build_speech_contexts(["Govee"], boost=0.0)
        with self.assertRaises(ValueError):
            build_speech_contexts(["Govee"], boost=6.0)
        with self.assertRaises(ValueError):
            build_speech_contexts([], boost=2.5)

    def test_commit_shape(self) -> None:
        self.assertEqual(build_commit(), {"type": "input_audio_buffer.commit"})


class RealtimeUrlTest(unittest.TestCase):
    def test_parse_explicit(self) -> None:
        host, port, path = parse_realtime_url(
            "ws://127.0.0.1:8080/v1/audio/transcriptions/realtime"
        )
        self.assertEqual(
            (host, port, path), ("127.0.0.1", 8080, "/v1/audio/transcriptions/realtime")
        )

    def test_rejects_non_ws(self) -> None:
        with self.assertRaises(ValueError):
            parse_realtime_url("http://127.0.0.1:8080/path")


class WsFrameTest(unittest.TestCase):
    def test_text_round_trip(self) -> None:
        frame = ws_encode_frame(0x1, b'{"type":"hi"}', mask=True)
        opcode, payload, consumed = ws_decode_frame(frame)
        self.assertEqual(opcode, 0x1)
        self.assertEqual(payload, b'{"type":"hi"}')
        self.assertEqual(consumed, len(frame))

    def test_binary_unmasked_round_trip(self) -> None:
        payload = bytes(range(256)) * 4
        frame = ws_encode_frame(0x2, payload, mask=False)
        opcode, decoded, _ = ws_decode_frame(frame)
        self.assertEqual(opcode, 0x2)
        self.assertEqual(decoded, payload)

    def test_incomplete_raises(self) -> None:
        with self.assertRaises(ValueError):
            ws_decode_frame(b"\x81")


class SummarizeTest(unittest.TestCase):
    def test_summary(self) -> None:
        summary = summarize([0.01, 0.02, 0.03])
        self.assertEqual(summary["count"], 3)
        self.assertAlmostEqual(summary["mean"], 0.02)
        self.assertAlmostEqual(summary["max"], 0.03)

    def test_empty(self) -> None:
        self.assertEqual(summarize([])["count"], 0)


if __name__ == "__main__":
    unittest.main()
