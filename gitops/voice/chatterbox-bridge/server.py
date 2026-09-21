#!/usr/bin/env python3
"""Wyoming TTS server for Chatterbox Turbo (stdlib + lazy torch).

Speaks the subset of the Wyoming protocol Home Assistant needs: per
connection, `describe` answers with one `info` event advertising the
`jarvis` voice, and each `synthesize` event answers with `audio-start`,
one or more `audio-chunk` events carrying 16-bit mono PCM, and
`audio-stop`. Streaming `synthesize-start/chunk/stop` sequences are
tolerated by buffering the text and synthesizing once on `stop`.

The Chatterbox model (torch, chatterbox-tts) is imported lazily inside
ChatterboxEngine.load so unit tests and `--help` never need the GPU
stack. Turns are serialized behind one asyncio lock; any engine
failure fails one turn (empty audio, which HA renders as silence)
and never kills the service.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import struct
from dataclasses import dataclass, field

LOG = logging.getLogger("chatterbox-bridge")

PROGRAM_NAME = "chatterbox-turbo"
DEFAULT_VOICE = "jarvis"
DEFAULT_LANGUAGE = "en"
TURBO_REPO = "ResembleAI/chatterbox-turbo"

_TAG_RE = re.compile(r"\[[^\[\]]{1,32}\]")


def strip_paralinguistic_tags(text: str) -> str:
    """Remove [laugh]-style tags HA replies must never vocalize."""
    cleaned = _TAG_RE.sub("", text)
    return re.sub(r"[ \t]{2,}", " ", cleaned).strip(" \t")


def samples_to_pcm16(samples) -> bytes:
    """Convert float samples in [-1, 1] to little-endian int16 PCM."""
    out = bytearray()
    for value in samples:
        scaled = int(round(float(value) * 32767.0))
        if scaled > 32767:
            scaled = 32767
        elif scaled < -32768:
            scaled = -32768
        out += struct.pack("<h", scaled)
    return bytes(out)


def chunk_pcm(pcm: bytes, chunk_bytes: int):
    for offset in range(0, len(pcm), chunk_bytes):
        yield pcm[offset : offset + chunk_bytes]


@dataclass
class TtsConfig:
    """Environment-driven server configuration (pure)."""

    port: int = 10201
    voice_name: str = DEFAULT_VOICE
    device: str = "cuda"
    model_dir: str = ""
    reference_wav: str = ""
    allow_tags: bool = False
    chunk_ms: int = 250
    temperature: float = 0.8
    top_k: int = 1000
    top_p: float = 0.95
    repetition_penalty: float = 1.2

    @classmethod
    def from_env(cls) -> TtsConfig:
        get = os.environ.get
        return cls(
            port=int(get("CHATTERBOX_PORT", "10201")),
            voice_name=get("CHATTERBOX_VOICE", DEFAULT_VOICE),
            device=get("CHATTERBOX_DEVICE", "cuda"),
            model_dir=get("CHATTERBOX_MODEL_DIR", ""),
            reference_wav=get("CHATTERBOX_REFERENCE", ""),
            allow_tags=get("CHATTERBOX_ALLOW_TAGS", "0") == "1",
            chunk_ms=int(get("CHATTERBOX_CHUNK_MS", "250")),
            temperature=float(get("CHATTERBOX_TEMPERATURE", "0.8")),
            top_k=int(get("CHATTERBOX_TOP_K", "1000")),
            top_p=float(get("CHATTERBOX_TOP_P", "0.95")),
            repetition_penalty=float(get("CHATTERBOX_REPETITION_PENALTY", "1.2")),
        )

    def validate(self) -> None:
        if not 1 <= self.port <= 65535:
            raise ValueError("CHATTERBOX_PORT must be a TCP port")
        if not self.voice_name.strip():
            raise ValueError("CHATTERBOX_VOICE must be nonempty")
        if self.device not in ("cuda", "cpu"):
            raise ValueError("CHATTERBOX_DEVICE must be cuda or cpu")
        if self.chunk_ms < 20 or self.chunk_ms > 2000:
            raise ValueError("CHATTERBOX_CHUNK_MS must be in [20, 2000]")
        if not 0.0 < self.temperature <= 2.0:
            raise ValueError("CHATTERBOX_TEMPERATURE must be in (0, 2]")
        if self.top_k < 1:
            raise ValueError("CHATTERBOX_TOP_K must be >= 1")
        if not 0.0 < self.top_p <= 1.0:
            raise ValueError("CHATTERBOX_TOP_P must be in (0, 1]")
        if not 1.0 <= self.repetition_penalty <= 2.0:
            raise ValueError("CHATTERBOX_REPETITION_PENALTY must be in [1, 2]")

    def chunk_bytes(self, rate: int) -> int:
        frames = max(1, rate * self.chunk_ms // 1000)
        return frames * 2


def resolve_reference(path: str) -> str | None:
    """Return the reference clip path when usable, else None (builtin voice)."""
    candidate = (path or "").strip()
    if not candidate:
        return None
    if not os.path.isfile(candidate):
        LOG.warning("reference clip %s missing, using builtin voice", candidate)
        return None
    if os.path.getsize(candidate) == 0:
        LOG.warning("reference clip %s is empty, using builtin voice", candidate)
        return None
    return candidate


class ChatterboxEngine:
    """Thin wrapper over ChatterboxTurboTTS (imports torch lazily)."""

    def __init__(self, config: TtsConfig) -> None:
        self._config = config
        self._model = None
        self._sample_rate = 24000

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def load(self) -> None:
        import torch

        from chatterbox.tts_turbo import ChatterboxTurboTTS

        config = self._config
        device = config.device
        if device == "cuda" and not torch.cuda.is_available():
            LOG.warning("CUDA unavailable, falling back to CPU")
            device = "cpu"
        if config.model_dir:
            LOG.info("loading Turbo weights from %s", config.model_dir)
            self._model = ChatterboxTurboTTS.from_local(config.model_dir, device=device)
        else:
            LOG.info("loading Turbo weights from %s", TURBO_REPO)
            self._model = ChatterboxTurboTTS.from_pretrained(device=device)
        self._sample_rate = int(self._model.sr)
        reference = resolve_reference(config.reference_wav)
        if reference is not None:
            try:
                self._model.prepare_conditionals(reference)
                LOG.info("voice conditionals prepared from %s", reference)
            except Exception:
                LOG.warning(
                    "reference clip %s rejected, using builtin voice",
                    reference,
                    exc_info=True,
                )

    def synthesize(self, text: str) -> tuple[bytes, int]:
        assert self._model is not None, "engine not loaded"
        config = self._config
        wav = self._model.generate(
            text,
            temperature=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
            repetition_penalty=config.repetition_penalty,
        )
        samples = wav.squeeze(0).detach().cpu().numpy().tolist()
        return samples_to_pcm16(samples), self._sample_rate


def encode_event(type_: str, data: dict | None = None, payload: bytes = b"") -> bytes:
    header: dict = {"type": type_}
    data_bytes = json.dumps(data or {}).encode() if data else b""
    if data_bytes:
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    return json.dumps(header).encode() + b"\n" + data_bytes + payload


async def read_event(reader: asyncio.StreamReader) -> dict | None:
    try:
        line = await reader.readline()
    except (asyncio.IncompleteReadError, ConnectionError):
        return None
    if not line:
        return None
    try:
        header = json.loads(line)
    except ValueError:
        return None
    data_length = int(header.get("data_length") or 0)
    payload_length = int(header.get("payload_length") or 0)
    data: dict = {}
    try:
        if data_length:
            raw = await reader.readexactly(data_length)
            parsed = json.loads(raw.decode())
            if isinstance(parsed, dict):
                data = parsed
        payload = b""
        if payload_length:
            payload = await reader.readexactly(payload_length)
    except (asyncio.IncompleteReadError, ConnectionError, ValueError):
        return None
    return {"type": header.get("type"), "data": data, "payload": payload}


def info_event(config: TtsConfig, version: str = "0.1.7") -> bytes:
    attribution = {
        "name": "Resemble AI",
        "url": "https://github.com/resemble-ai/chatterbox",
    }
    return encode_event(
        "info",
        {
            "tts": [
                {
                    "name": PROGRAM_NAME,
                    "description": "Chatterbox Turbo TTS",
                    "attribution": attribution,
                    "installed": True,
                    "version": version,
                    "languages": [DEFAULT_LANGUAGE],
                    "voices": [
                        {
                            "name": config.voice_name,
                            "description": "Jarvis voice (cloned reference or builtin)",
                            "attribution": attribution,
                            "installed": True,
                            "languages": [DEFAULT_LANGUAGE],
                        }
                    ],
                    "supports_synthesize_streaming": False,
                }
            ]
        },
    )


@dataclass
class TtsServer:
    config: TtsConfig
    engine: object
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    def _prepare_text(self, text: str) -> str:
        if not self.config.allow_tags:
            text = strip_paralinguistic_tags(text)
        return text.strip()

    async def _send_audio(
        self, writer: asyncio.StreamWriter, pcm: bytes, rate: int
    ) -> None:
        writer.write(
            encode_event("audio-start", {"rate": rate, "width": 2, "channels": 1})
        )
        for piece in chunk_pcm(pcm, self.config.chunk_bytes(rate)):
            writer.write(encode_event("audio-chunk", {}, piece))
        writer.write(encode_event("audio-stop", {}))
        await writer.drain()

    async def _send_silence(self, writer: asyncio.StreamWriter) -> None:
        writer.write(
            encode_event("audio-start", {"rate": 24000, "width": 2, "channels": 1})
        )
        writer.write(encode_event("audio-stop", {}))
        await writer.drain()

    async def synthesize_turn(
        self, writer: asyncio.StreamWriter, text: str, voice: str | None
    ) -> None:
        prepared = self._prepare_text(text)
        if voice and voice != self.config.voice_name:
            LOG.info("unknown voice %r, using %r", voice, self.config.voice_name)
        if not prepared:
            await self._send_silence(writer)
            return
        try:
            async with self._lock:
                pcm, rate = await asyncio.to_thread(self.engine.synthesize, prepared)
        except Exception:
            LOG.warning("synthesis failed, sending silence", exc_info=True)
            await self._send_silence(writer)
            return
        await self._send_audio(writer, pcm, rate)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        pending_text: list[str] = []
        try:
            while True:
                event = await read_event(reader)
                if event is None:
                    break
                kind = event["type"]
                data = event["data"]
                if kind == "describe":
                    writer.write(info_event(self.config))
                    await writer.drain()
                elif kind == "synthesize":
                    voice = (data.get("voice") or {}).get("name")
                    await self.synthesize_turn(writer, data.get("text", ""), voice)
                elif kind == "synthesize-chunk":
                    pending_text.append(str(data.get("text", "")))
                elif kind == "synthesize-stop":
                    voice = (data.get("voice") or {}).get("name")
                    await self.synthesize_turn(writer, "".join(pending_text), voice)
                    pending_text = []
                elif kind == "synthesize-start":
                    pending_text = []
        finally:
            try:
                writer.close()
            except (ConnectionError, RuntimeError):
                pass


async def amain() -> None:
    parser = argparse.ArgumentParser(description="Chatterbox Turbo Wyoming TTS server")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    config = TtsConfig.from_env()
    if args.port is not None:
        config.port = args.port
    config.validate()
    logging.basicConfig(level=logging.INFO)
    engine = ChatterboxEngine(config)
    await asyncio.to_thread(engine.load)
    server = TtsServer(config, engine)
    tcp = await asyncio.start_server(server.handle_client, "0.0.0.0", config.port)
    LOG.info("listening on %d", config.port)
    async with tcp:
        await tcp.serve_forever()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
