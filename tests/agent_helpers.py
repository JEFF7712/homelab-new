from __future__ import annotations

import subprocess
from pathlib import Path


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        capture_output=True,
        check=True,
    ).stdout


def make_repository(path: Path) -> Path:
    git(path, "init", "-q", "-b", "main")
    config = path / ".git" / "config"
    with config.open("a", encoding="utf-8") as handle:
        handle.write(
            "[user]\n\tname = Agent Test\n\temail = agent-test@example.invalid\n"
        )
    return path


def commit(repository: Path, message: str) -> None:
    git(repository, "add", "-A")
    git(repository, "commit", "-qm", message)
