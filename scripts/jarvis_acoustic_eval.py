"""Replay labeled QuadCast WAV recordings through Wyoming STT backends."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import wave
from pathlib import Path

from gitops.voice.gateway.gateway import encode_event, read_event

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = ROOT / "tests/acoustic/manifest.json"


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def word_error_rate(expected: str, observed: str) -> float:
    left, right = normalize(expected).split(), normalize(observed).split()
    row = list(range(len(right) + 1))
    for i, expected_word in enumerate(left, 1):
        next_row = [i]
        for j, observed_word in enumerate(right, 1):
            next_row.append(
                min(
                    next_row[-1] + 1,
                    row[j] + 1,
                    row[j - 1] + (expected_word != observed_word),
                )
            )
        row = next_row
    return row[-1] / max(1, len(left))


def load_manifest(path: Path) -> list[dict]:
    payload = json.loads(path.read_text())
    cases = payload.get("cases")
    if not isinstance(cases, list) or not 10 <= len(cases) <= 20:
        raise ValueError("acoustic corpus must contain 10 to 20 labeled cases")
    required = {"id", "recording", "expected", "category"}
    for case in cases:
        if not isinstance(case, dict) or not required <= case.keys():
            raise ValueError(
                "every acoustic case needs id, recording, expected, category"
            )
        recording = path.parent / case["recording"]
        if not recording.is_file():
            raise ValueError(f"missing recording: {recording}")
    return cases


async def transcribe(host: str, port: int, recording: Path) -> str:
    with wave.open(str(recording), "rb") as source:
        if source.getcomptype() != "NONE":
            raise ValueError(f"{recording} must be uncompressed PCM WAV")
        fmt = {
            "rate": source.getframerate(),
            "width": source.getsampwidth(),
            "channels": source.getnchannels(),
        }
        pcm = source.readframes(source.getnframes())
    reader, writer = await asyncio.open_connection(host, port)
    writer.write(encode_event({"type": "transcribe", "data": {"language": "en"}}))
    writer.write(encode_event({"type": "audio-start", "data": fmt}))
    chunk_bytes = fmt["rate"] * fmt["width"] * fmt["channels"] // 10
    for offset in range(0, len(pcm), chunk_bytes):
        writer.write(
            encode_event(
                {
                    "type": "audio-chunk",
                    "data": fmt,
                    "payload": pcm[offset : offset + chunk_bytes],
                }
            )
        )
    writer.write(encode_event({"type": "audio-stop", "data": {}}))
    await writer.drain()
    while (event := await asyncio.wait_for(read_event(reader), 30)) is not None:
        if event["type"] == "transcript":
            writer.close()
            await writer.wait_closed()
            return str(event["data"].get("text", ""))
    return ""


async def run(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest)
    cases = load_manifest(manifest)
    results = []
    for case in cases:
        observed = await transcribe(
            args.host, args.port, manifest.parent / case["recording"]
        )
        wer = word_error_rate(case["expected"], observed)
        results.append(
            {**case, "observed": observed, "wer": wer, "ok": wer <= args.max_wer}
        )
    print(json.dumps({"backend": args.backend, "results": results}, indent=2))
    return 0 if all(result["ok"] for result in results) else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=10300)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--max-wer", type=float, default=0.15)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
