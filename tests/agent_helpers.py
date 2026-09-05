from __future__ import annotations

from pathlib import Path
import subprocess


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
    ).stdout


def make_repository(path: Path) -> Path:
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", "Agent Test")
    git(path, "config", "user.email", "agent-test@example.invalid")
    return path


def commit(repository: Path, message: str) -> None:
    git(repository, "add", "-A")
    git(repository, "commit", "-qm", message)
