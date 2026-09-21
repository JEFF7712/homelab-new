"""Offline-first Nemotron streaming STT benchmark harness for Jarvis.

Phase-one contract: Wyoming owns utterance segmentation, Nemotron owns
recognition. Endpointing stays disabled; the harness drives
audio-start/chunk/stop replay and measures T0-T4 finalization latency,
WER / named-entity recall, and Qwen contention on the shared T1000.

Live replay needs a reachable Wyoming TCP endpoint, a nemo-speech
realtime WebSocket URL, or an Ollama host. All math, framing, and
scoring helpers are pure stdlib so unit tests run offline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import struct
import subprocess
import time
import urllib.request
from dataclasses import dataclass

DEFAULT_SAMPLE_RATE = 16000
DEFAULT_LANGUAGE = "en-US"
DEFAULT_BOOST = 2.5
DEFAULT_CHUNK_MS = 100
MAX_BOOST = 5.0

DEFAULT_VOCAB_PHRASES = [
    "Govee",
    "downstairs",
    "living room",
    "bedroom",
    "kitchen",
    "tulip lamp",
    "mushroom lamp",
    "floor lamp",
    "desk lamp",
    "light strip",
    "good vibes sign",
    "Spotify",
    "Young Thug",
    "The Weeknd",
    "Kendrick Lamar",
    "Drake",
    "Travis Scott",
    "Kanye West",
    "Frank Ocean",
    "Marvin Gaye",
    "Metro Boomin",
    "Jarvis",
]


@dataclass
class TurnTimestamps:
    """Monotonic timestamps for one benchmark turn (seconds)."""

    t0_first_chunk: float
    t1_last_sample: float
    t2_audio_stop: float
    t3_final_transcript: float
    t4_returned_to_ha: float

    def metrics(self) -> dict[str, float]:
        vad_latency = self.t2_audio_stop - self.t1_last_sample
        asr_finalization = self.t3_final_transcript - self.t2_audio_stop
        proxy_overhead = self.t4_returned_to_ha - self.t3_final_transcript
        stt_post_speech = self.t4_returned_to_ha - self.t2_audio_stop
        voice_post_speech = self.t4_returned_to_ha - self.t1_last_sample
        return {
            "vad_latency": vad_latency,
            "asr_finalization": asr_finalization,
            "proxy_overhead": proxy_overhead,
            "stt_post_speech": stt_post_speech,
            "voice_post_speech": voice_post_speech,
        }


def normalize_text(text: str) -> str:
    clean = text.strip().lower()
    for punct in ".!?,;:\"'()[]":
        clean = clean.replace(punct, "")
    return " ".join(clean.split())


def wer(reference: str, hypothesis: str) -> float:
    ref = normalize_text(reference).split()
    hyp = normalize_text(hypothesis).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    if not hyp:
        return 1.0
    prev = list(range(len(hyp) + 1))
    for i, ref_word in enumerate(ref, start=1):
        cur = [i] + [0] * len(hyp)
        for j, hyp_word in enumerate(hyp, start=1):
            cost = 0 if ref_word == hyp_word else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[len(hyp)] / len(ref)


def entity_recall(
    expected_phrases: list[str], hypothesis: str
) -> tuple[float, dict[str, bool]]:
    norm_hyp = normalize_text(hypothesis)
    details: dict[str, bool] = {}
    for phrase in expected_phrases:
        norm_phrase = normalize_text(phrase)
        if not norm_phrase:
            continue
        details[phrase] = norm_phrase in norm_hyp
    if not details:
        return 1.0, {}
    hits = sum(1 for hit in details.values() if hit)
    return hits / len(details), details


def score_turn(
    reference: str, hypothesis: str, entities: list[str] | None = None
) -> dict[str, object]:
    recall, details = entity_recall(entities or [], hypothesis)
    return {
        "wer": wer(reference, hypothesis),
        "entity_recall": recall,
        "entity_details": details,
        "n_ref_words": len(normalize_text(reference).split()),
    }


def summarize(values: list[float]) -> dict[str, float]:
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    p50 = statistics.median(ordered)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "count": float(len(ordered)),
        "mean": statistics.fmean(ordered),
        "p50": p50,
        "p95": float(ordered[p95_index]),
        "max": float(ordered[-1]),
    }


def summarize_metric(turns: list[dict[str, object]]) -> dict[str, object]:
    keys = (
        "vad_latency",
        "asr_finalization",
        "proxy_overhead",
        "stt_post_speech",
        "voice_post_speech",
    )
    summary: dict[str, object] = {}
    for key in keys:
        values = [
            float(t["metrics"][key])  # type: ignore[index]
            for t in turns
            if isinstance(t.get("metrics"), dict) and key in t["metrics"]  # type: ignore[operator]
        ]
        summary[key] = summarize(values)
    wers = [
        float(t["score"]["wer"])  # type: ignore[index]
        for t in turns
        if isinstance(t.get("score"), dict)
    ]
    if wers:
        summary["wer"] = summarize(wers)
    return summary
    if not values:
        return {"count": 0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    p50 = statistics.median(ordered)
    p95_index = min(len(ordered) - 1, int(0.95 * len(ordered)))
    return {
        "count": float(len(ordered)),
        "mean": statistics.fmean(ordered),
        "p50": p50,
        "p95": float(ordered[p95_index]),
        "max": float(ordered[-1]),
    }


def encode_wyoming(
    event_type: str, data: dict[str, object] | None = None, payload: bytes = b""
) -> bytes:
    data_bytes = json.dumps(data or {}).encode() if data else b""
    header: dict[str, object] = {"type": event_type}
    if data_bytes:
        header["data_length"] = len(data_bytes)
    if payload:
        header["payload_length"] = len(payload)
    return json.dumps(header).encode() + b"\n" + data_bytes + payload


def decode_wyoming_frame(buffer: bytes) -> tuple[dict[str, object], bytes]:
    line, sep, rest = buffer.partition(b"\n")
    if not sep:
        raise ValueError("incomplete wyoming header line")
    header = json.loads(line.decode())
    data: dict[str, object] = {}
    data_length = int(header.get("data_length") or 0)
    payload_length = int(header.get("payload_length") or 0)
    if len(rest) < data_length + payload_length:
        raise ValueError("incomplete wyoming frame body")
    if data_length:
        raw = rest[:data_length]
        parsed = json.loads(raw.decode())
        if isinstance(parsed, dict):
            data = parsed
    payload = rest[data_length : data_length + payload_length]
    remaining = rest[data_length + payload_length :]
    event: dict[str, object] = {
        "type": header.get("type"),
        "data": data,
        "payload": payload,
    }
    return event, remaining


async def read_wyoming_event(
    reader: asyncio.StreamReader,
) -> dict[str, object] | None:
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
    data: dict[str, object] = {}
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


async def write_wyoming_event(
    writer: asyncio.StreamWriter,
    event_type: str,
    data: dict[str, object] | None = None,
    payload: bytes = b"",
) -> None:
    writer.write(encode_wyoming(event_type, data, payload))
    await writer.drain()


def chunk_pcm(
    pcm: bytes, chunk_ms: int, rate: int = 16000, width: int = 2, channels: int = 1
) -> list[bytes]:
    if chunk_ms <= 0:
        raise ValueError("chunk_ms must be positive")
    frame_bytes = rate * chunk_ms // 1000 * width * channels
    if frame_bytes <= 0:
        raise ValueError("chunk parameters produce empty frames")
    return [pcm[i : i + frame_bytes] for i in range(0, len(pcm), frame_bytes)]


def build_speech_contexts(
    phrases: list[str], boost: float = DEFAULT_BOOST
) -> list[dict[str, object]]:
    cleaned = [p.strip() for p in phrases if p.strip()]
    if not cleaned:
        raise ValueError("at least one boosting phrase is required")
    if not 0 < boost <= MAX_BOOST:
        raise ValueError(f"boost must be in (0, {MAX_BOOST}]")
    return [{"phrases": cleaned, "boost": float(boost)}]


def build_session_update(
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    language: str = DEFAULT_LANGUAGE,
    speech_contexts: list[dict[str, object]] | None = None,
    endpointing_ms: float | None = None,
    word_timestamps: bool = False,
) -> dict[str, object]:
    session: dict[str, object] = {
        "sample_rate": sample_rate,
        "language": language,
        "word_timestamps": word_timestamps,
    }
    if speech_contexts is not None:
        session["speech_contexts"] = speech_contexts
    if endpointing_ms is not None:
        session["endpointing_ms"] = endpointing_ms
    return {"type": "session.update", "session": session}


def build_commit() -> dict[str, object]:
    return {"type": "input_audio_buffer.commit"}


def ws_encode_frame(opcode: int, payload: bytes, mask: bool = True) -> bytes:
    first = 0x80 | (opcode & 0x0F)
    mask_bit = 0x80 if mask else 0
    length = len(payload)
    if length < 126:
        header = struct.pack("!BB", first, mask_bit | length)
    elif length < 65536:
        header = struct.pack("!BBH", first, mask_bit | 126, length)
    else:
        header = struct.pack("!BBQ", first, mask_bit | 127, length)
    if not mask:
        return header + payload
    mask_key = os.urandom(4)
    masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return header + mask_key + masked


def ws_decode_frame(buffer: bytes) -> tuple[int, bytes, int]:
    if len(buffer) < 2:
        raise ValueError("incomplete websocket header")
    first, second = buffer[0], buffer[1]
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    offset = 2
    if length == 126:
        if len(buffer) < 4:
            raise ValueError("incomplete websocket extended length")
        (length,) = struct.unpack("!H", buffer[2:4])
        offset = 4
    elif length == 127:
        if len(buffer) < 10:
            raise ValueError("incomplete websocket 64-bit length")
        (length,) = struct.unpack("!Q", buffer[2:10])
        offset = 10
    mask_key = b""
    if masked:
        if len(buffer) < offset + 4:
            raise ValueError("incomplete websocket mask")
        mask_key = buffer[offset : offset + 4]
        offset += 4
    if len(buffer) < offset + length:
        raise ValueError("incomplete websocket payload")
    payload = buffer[offset : offset + length]
    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return opcode, payload, offset + length


def parse_realtime_url(url: str) -> tuple[str, int, str]:
    if not url.startswith("ws://"):
        raise ValueError("only ws:// realtime URLs are supported in phase one")
    rest = url[len("ws://") :]
    host_port, _, path = rest.partition("/")
    host, _, port_text = host_port.partition(":")
    if not host:
        raise ValueError(f"invalid realtime URL: {url}")
    port = int(port_text) if port_text else 80
    return host, port, "/" + path if path else "/"


async def ws_handshake(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter, host: str, path: str
) -> None:
    import base64 as _base64

    key = _base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    )
    writer.write(request.encode())
    await writer.drain()
    header = await reader.readuntil(b"\r\n\r\n")
    status = header.decode(errors="replace").splitlines()[0] if header else ""
    if "101" not in status:
        raise ConnectionError(f"websocket handshake failed: {status}")


async def ws_send_text(writer: asyncio.StreamWriter, obj: dict[str, object]) -> None:
    writer.write(ws_encode_frame(0x1, json.dumps(obj).encode(), mask=True))
    await writer.drain()


async def ws_send_binary(writer: asyncio.StreamWriter, data: bytes) -> None:
    writer.write(ws_encode_frame(0x2, data, mask=True))
    await writer.drain()


async def ws_recv_text_or_binary(
    reader: asyncio.StreamReader, buf: bytearray
) -> tuple[int, bytes]:
    while True:
        chunk = await reader.read(65536)
        if not chunk:
            raise ConnectionError("websocket closed")
        buf += chunk
        try:
            opcode, payload, consumed = ws_decode_frame(bytes(buf))
        except ValueError:
            continue
        del buf[:consumed]
        if opcode == 0x9:  # ping
            continue
        if opcode == 0x8:  # close
            raise ConnectionError("websocket closed by server")
        return opcode, payload


async def replay_nemotron_turn(
    url: str,
    pcm: bytes,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    language: str = DEFAULT_LANGUAGE,
    phrases: list[str] | None = None,
    boost: float = DEFAULT_BOOST,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    pace: bool = True,
    timeout: float = 60.0,
) -> tuple[TurnTimestamps, str, int]:
    host, port, path = parse_realtime_url(url)
    contexts = build_speech_contexts(phrases or []) if phrases else None
    session_update = build_session_update(
        sample_rate=sample_rate, language=language, speech_contexts=contexts
    )
    reader, writer = await asyncio.open_connection(host, port)
    try:
        await ws_handshake(reader, writer, host, path)
        await ws_send_text(writer, session_update)
        buf = bytearray()
        deltas = 0
        t0 = time.monotonic()
        for chunk in chunk_pcm(pcm, chunk_ms, rate=sample_rate):
            await ws_send_binary(writer, chunk)
            if pace:
                await asyncio.sleep(chunk_ms / 1000.0)
        t1 = time.monotonic()
        await ws_send_text(writer, build_commit())
        t2 = time.monotonic()
        text = ""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            opcode, payload = await ws_recv_text_or_binary(reader, buf)
            if opcode == 0x2:
                continue
            try:
                event = json.loads(payload.decode())
            except ValueError:
                continue
            event_type = event.get("type", "")
            if "delta" in event_type:
                deltas += 1
            if event_type.endswith(".completed"):
                transcript = event.get("transcript", "")
                if isinstance(transcript, str) and transcript:
                    text = transcript
                    break
                item = event.get("item", {})
                if isinstance(item, dict):
                    content = item.get("content", "")
                    if isinstance(content, str) and content:
                        text = content
                        break
            if event_type == "error":
                raise RuntimeError(f"realtime error: {payload.decode()[:200]}")
        t3 = time.monotonic()
        return TurnTimestamps(t0, t1, t2, t3, t3), text, deltas
    finally:
        writer.close()


async def replay_wyoming_turn(
    host: str,
    port: int,
    pcm: bytes,
    rate: int = DEFAULT_SAMPLE_RATE,
    chunk_ms: int = DEFAULT_CHUNK_MS,
    language: str = "en",
    pace: bool = False,
) -> tuple[TurnTimestamps, str]:
    import socket as _socket

    reader, writer = await asyncio.open_connection(host, port)
    sock = writer.transport.get_extra_info("socket")
    if sock is not None:
        sock.setsockopt(_socket.IPPROTO_TCP, _socket.TCP_NODELAY, 1)
    try:
        await write_wyoming_event(writer, "transcribe", {"language": language})
        await write_wyoming_event(
            writer, "audio-start", {"rate": rate, "width": 2, "channels": 1}
        )
        t0 = time.monotonic()
        chunks = chunk_pcm(pcm, chunk_ms, rate=rate)
        for chunk in chunks:
            await write_wyoming_event(
                writer,
                "audio-chunk",
                {"rate": rate, "width": 2, "channels": 1},
                chunk,
            )
            if pace:
                await asyncio.sleep(chunk_ms / 1000.0)
        t1 = time.monotonic()
        await write_wyoming_event(writer, "audio-stop")
        t2 = time.monotonic()
        text = ""
        while True:
            event = await read_wyoming_event(reader)
            if event is None:
                break
            if event.get("type") == "transcript":
                data = event.get("data")
                if isinstance(data, dict):
                    raw = data.get("text", "")
                    text = raw if isinstance(raw, str) else ""
                break
        t3 = time.monotonic()
        stamps = TurnTimestamps(t0, t1, t2, t3, t3)
        return stamps, text
    finally:
        writer.close()


def ollama_placement(host: str, timeout: float = 10.0) -> dict[str, object]:
    url = host.rstrip("/") + "/api/ps"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "payload": payload}


def ollama_generate_probe(
    host: str,
    model: str,
    prompt: str = "Reply with the word OK.",
    timeout: float = 120.0,
) -> dict[str, object]:
    url = host.rstrip("/") + "/api/generate"
    body = json.dumps({"model": model, "prompt": prompt, "stream": True}).encode()
    request = urllib.request.Request(url, data=body, method="POST")
    start = time.monotonic()
    first_token: float | None = None
    text_parts: list[str] = []
    eval_count: int | None = None
    eval_duration_ns: int | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for line in response:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line.decode())
                except ValueError:
                    continue
                if first_token is None and msg.get("response"):
                    first_token = time.monotonic()
                part = msg.get("response", "")
                if isinstance(part, str):
                    text_parts.append(part)
                if msg.get("done") is True:
                    count = msg.get("eval_count")
                    duration = msg.get("eval_duration")
                    eval_count = count if isinstance(count, int) else None
                    eval_duration_ns = duration if isinstance(duration, int) else None
                    break
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    end = time.monotonic()
    ttft = (first_token - start) if first_token is not None else (end - start)
    total = end - start
    tokens_per_s: float | None = None
    if eval_count and eval_duration_ns:
        tokens_per_s = eval_count / (eval_duration_ns / 1e9)
    return {
        "ok": True,
        "ttft_s": ttft,
        "total_s": total,
        "tokens_per_s": tokens_per_s,
        "text": "".join(text_parts),
    }


def nvidia_smi_snapshot() -> dict[str, object] | None:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,utilization.gpu,memory.used,memory.total",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    gpus: list[dict[str, float]] = []
    for line in result.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 4:
            continue
        try:
            gpus.append(
                {
                    "index": float(parts[0]),
                    "util_pct": float(parts[1]),
                    "mem_used_mib": float(parts[2]),
                    "mem_total_mib": float(parts[3]),
                }
            )
        except ValueError:
            continue
    return {"gpus": gpus} if gpus else None


def load_pcm_16k_mono(path: str) -> tuple[bytes, int]:
    import wave

    with wave.open(path, "rb") as wav:
        rate = wav.getframerate()
        width = wav.getsampwidth()
        channels = wav.getnchannels()
        frames = wav.readframes(wav.getnframes())
    if rate != DEFAULT_SAMPLE_RATE or width != 2 or channels != 1:
        raise ValueError(
            f"{path}: need 16kHz 16-bit mono WAV, "
            f"got {rate}Hz width={width} channels={channels}"
        )
    return frames, rate


def cmd_score(args: argparse.Namespace) -> int:
    result = score_turn(args.reference, args.hypothesis, args.entity or [])
    print(json.dumps(result, indent=2))
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    contexts = None
    if args.phrase:
        contexts = build_speech_contexts(args.phrase, boost=args.boost)
    endpointing = args.endpointing_ms if args.endpointing_ms else None
    payload = build_session_update(
        sample_rate=args.sample_rate,
        language=args.language,
        speech_contexts=contexts,
        endpointing_ms=endpointing,
        word_timestamps=args.word_timestamps,
    )
    print(json.dumps(payload, indent=2))
    return 0


def cmd_replay_wyoming(args: argparse.Namespace) -> int:
    async def run() -> int:
        pcm, rate = load_pcm_16k_mono(args.wav)
        turns: list[dict[str, object]] = []
        for i in range(args.repeat):
            if i > 0 and args.pause_ms > 0:
                await asyncio.sleep(args.pause_ms / 1000.0)
            stamps, text = await replay_wyoming_turn(
                args.host,
                args.port,
                pcm,
                rate=rate,
                chunk_ms=args.chunk_ms,
                pace=args.pace,
            )
            turn: dict[str, object] = {
                "metrics": stamps.metrics(),
                "transcript": text,
            }
            if args.reference:
                turn["score"] = score_turn(args.reference, text, args.entity or [])
            turns.append(turn)
        output: dict[str, object] = {
            "turns": turns,
            "summary": summarize_metric(turns),
        }
        if args.reference:
            output["score"] = score_turn(
                args.reference,
                str(turns[-1]["transcript"]),
                args.entity or [],
            )
        print(json.dumps(output, indent=2))
        return 0

    return asyncio.run(run())


def cmd_replay_nemotron(args: argparse.Namespace) -> int:
    async def run() -> int:
        pcm, rate = load_pcm_16k_mono(args.wav)
        stamps, text, deltas = await replay_nemotron_turn(
            args.url,
            pcm,
            sample_rate=rate,
            language=args.language,
            phrases=args.phrase or None,
            boost=args.boost,
            chunk_ms=args.chunk_ms,
            pace=not args.no_pace,
            timeout=args.timeout,
        )
        output: dict[str, object] = {
            "timestamps": {
                "t0": stamps.t0_first_chunk,
                "t1": stamps.t1_last_sample,
                "t2": stamps.t2_audio_stop,
                "t3": stamps.t3_final_transcript,
                "t4": stamps.t4_returned_to_ha,
            },
            "metrics": stamps.metrics(),
            "transcript": text,
            "partial_deltas": deltas,
        }
        if args.reference:
            output["score"] = score_turn(args.reference, text, args.entity or [])
        print(json.dumps(output, indent=2))
        return 0

    return asyncio.run(run())


def cmd_ollama_probe(args: argparse.Namespace) -> int:
    output: dict[str, object] = {
        "placement": ollama_placement(args.host, timeout=args.timeout),
        "generate": ollama_generate_probe(
            args.host, args.model, prompt=args.prompt, timeout=args.timeout
        ),
        "gpu": nvidia_smi_snapshot(),
    }
    print(json.dumps(output, indent=2))
    ok = bool(output["placement"]) and bool(output["generate"])
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    score = sub.add_parser("score", help="Score one reference/hypothesis pair")
    score.add_argument("--reference", required=True)
    score.add_argument("--hypothesis", required=True)
    score.add_argument("--entity", action="append", default=[])
    score.set_defaults(func=cmd_score)

    session = sub.add_parser("session", help="Print a realtime session.update payload")
    session.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    session.add_argument("--language", default=DEFAULT_LANGUAGE)
    session.add_argument("--phrase", action="append", default=[])
    session.add_argument("--boost", type=float, default=DEFAULT_BOOST)
    session.add_argument("--endpointing-ms", type=float, default=0.0)
    session.add_argument("--word-timestamps", action="store_true")
    session.set_defaults(func=cmd_session)

    replay = sub.add_parser(
        "replay-wyoming", help="Replay a WAV through a Wyoming STT endpoint"
    )
    replay.add_argument("--host", required=True)
    replay.add_argument("--port", type=int, required=True)
    replay.add_argument("--wav", required=True)
    replay.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    replay.add_argument("--reference", default="")
    replay.add_argument("--entity", action="append", default=[])
    replay.add_argument("--repeat", type=int, default=1)
    replay.add_argument("--pause-ms", type=int, default=500)
    replay.add_argument("--pace", action="store_true")
    replay.set_defaults(func=cmd_replay_wyoming)

    nemotron = sub.add_parser(
        "replay-nemotron", help="Replay a WAV through Nemotron realtime WebSocket"
    )
    nemotron.add_argument(
        "--url", default="ws://127.0.0.1:8080/v1/audio/transcriptions/realtime"
    )
    nemotron.add_argument("--wav", required=True)
    nemotron.add_argument("--language", default=DEFAULT_LANGUAGE)
    nemotron.add_argument("--phrase", action="append", default=[])
    nemotron.add_argument("--boost", type=float, default=DEFAULT_BOOST)
    nemotron.add_argument("--chunk-ms", type=int, default=DEFAULT_CHUNK_MS)
    nemotron.add_argument("--no-pace", action="store_true")
    nemotron.add_argument("--timeout", type=float, default=60.0)
    nemotron.add_argument("--reference", default="")
    nemotron.add_argument("--entity", action="append", default=[])
    nemotron.set_defaults(func=cmd_replay_nemotron)

    probe = sub.add_parser(
        "ollama-probe", help="Measure Qwen TTFT/tok/s plus GPU snapshot"
    )
    probe.add_argument("--host", default="http://127.0.0.1:11434")
    probe.add_argument("--model", default="qwen2.5:3b")
    probe.add_argument("--prompt", default="Reply with the word OK.")
    probe.add_argument("--timeout", type=float, default=120.0)
    probe.set_defaults(func=cmd_ollama_probe)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
