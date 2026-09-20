"""Flip the Jarvis STT backend between local CPU whisper and Groq cloud.

Edits the wyoming-whisper Service selector, commits, and pushes so Flux
rolls the switch. Usage: just voice-stt cloud | just voice-stt local
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SELECTOR_FILE = REPO_ROOT / "gitops" / "voice" / "whisper.yaml"
BACKENDS = ("local", "cloud")


def run(*args: str) -> str:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(args)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in BACKENDS:
        raise SystemExit(f"usage: voice_stt_switch.py [{'|'.join(BACKENDS)}]")
    backend = sys.argv[1]

    text = SELECTOR_FILE.read_text()
    old = None
    for candidate in BACKENDS:
        if f"    backend: {candidate}\n" in text:
            old = candidate
            break
    if old is None:
        raise SystemExit("no backend selector found in gitops/voice/whisper.yaml")
    if old == backend:
        print(f"STT backend already {backend}, nothing to do")
        return

    SELECTOR_FILE.write_text(text.replace(f"    backend: {old}\n", f"    backend: {backend}\n", 1))
    run("git", "add", "gitops/voice/whisper.yaml")
    run("git", "commit", "-m", f"feat(voice): switch STT backend to {backend}")
    run("git", "push")
    print(f"STT backend switched {old} -> {backend}; Flux will roll it out")


if __name__ == "__main__":
    main()
