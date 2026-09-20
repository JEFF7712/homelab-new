from __future__ import annotations

import asyncio
import io
import unittest
import wave
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_bridge_module() -> dict:
    docs = list(
        yaml.safe_load_all(
            (REPO_ROOT / "gitops" / "voice" / "stt-groq.yaml").read_text()
        )
    )
    code = next(
        doc["data"]["bridge.py"]
        for doc in docs
        if doc.get("kind") == "ConfigMap"
        and doc["metadata"]["name"] == "stt-groq-bridge-code"
    )
    module: dict = {"__name__": "stt_groq_bridge_under_test"}
    exec(compile(code, "bridge.py", "exec"), module)
    return module


BRIDGE = load_bridge_module()


async def feed(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


class BridgeFrameTest(unittest.TestCase):
    def test_encode_decode_round_trip(self) -> None:
        async def run() -> dict | None:
            line = BRIDGE["encode_event"]("audio-start", {"rate": 16000, "width": 2, "channels": 1})
            return await BRIDGE["read_event"](await feed(line))

        event = asyncio.run(run())
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["type"], "audio-start")
        self.assertEqual(event["data"]["rate"], 16000)

    def test_encode_without_data(self) -> None:
        async def run() -> dict | None:
            return await BRIDGE["read_event"](await feed(BRIDGE["encode_event"]("audio-stop")))

        event = asyncio.run(run())
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event["type"], "audio-stop")
        self.assertEqual(event["data"], {})

    def test_decode_eof_returns_none(self) -> None:
        async def run() -> dict | None:
            return await BRIDGE["read_event"](await feed(b""))

        self.assertIsNone(asyncio.run(run()))

    def test_decode_garbage_returns_none(self) -> None:
        async def run() -> dict | None:
            return await BRIDGE["read_event"](await feed(b"not json\n"))

        self.assertIsNone(asyncio.run(run()))

    def test_info_advertises_asr_model(self) -> None:
        async def run() -> dict | None:
            return await BRIDGE["read_event"](await feed(BRIDGE["info_event"]("whisper-large-v3-turbo")))

        event = asyncio.run(run())
        assert event is not None
        self.assertEqual(event["type"], "info")
        program = event["data"]["asr"][0]
        self.assertEqual(program["models"][0]["name"], "whisper-large-v3-turbo")
        self.assertIn("en", program["models"][0]["languages"])


class BridgeAudioTest(unittest.TestCase):
    def test_pcm_to_wav_round_trip(self) -> None:
        pcm = b"\x00\x01" * 8000
        blob = BRIDGE["pcm_to_wav"](pcm, 16000, 2, 1)
        self.assertTrue(blob.startswith(b"RIFF"))
        with wave.open(io.BytesIO(blob), "rb") as wav:
            self.assertEqual(
                (wav.getframerate(), wav.getsampwidth(), wav.getnchannels()),
                (16000, 2, 1),
            )
            self.assertEqual(wav.readframes(wav.getnframes()), pcm)

    def test_multipart_shape(self) -> None:
        body, content_type = BRIDGE["build_multipart"](
            {"model": "m", "temperature": "0"}, "file", "audio.wav", b"data"
        )
        self.assertIn("multipart/form-data; boundary=", content_type)
        text = body.decode("latin1")
        self.assertIn('name="model"', text)
        self.assertIn('name="file"; filename="audio.wav"', text)
        self.assertIn("Content-Type: audio/wav", text)
        self.assertTrue(text.rstrip().endswith("--"))

    def test_default_prompt_covers_govee(self) -> None:
        self.assertIn("Govee", BRIDGE["DEFAULT_PROMPT"])


if __name__ == "__main__":
    unittest.main()
