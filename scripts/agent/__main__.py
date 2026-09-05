from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Sequence


UNAVAILABLE = 69


def git(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "git command failed"
        raise RuntimeError(message)
    return result.stdout


def nul_paths(output: str) -> list[str]:
    return [path for path in output.split("\0") if path]


def context_payload() -> dict[str, object]:
    root = Path(git("rev-parse", "--show-toplevel").strip()).resolve()
    head = git("rev-parse", "HEAD", cwd=root).strip()
    branch_result = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None
    staged = nul_paths(git("diff", "--cached", "--name-only", "-z", cwd=root))
    unstaged = nul_paths(git("diff", "--name-only", "-z", cwd=root))
    untracked = nul_paths(
        git("ls-files", "--others", "--exclude-standard", "-z", cwd=root)
    )
    files = sorted(set(staged) | set(unstaged) | set(untracked))
    return {
        "schema_version": 1,
        "command": "context",
        "repository": {
            "root": str(root),
            "branch": branch,
            "detached": branch is None,
            "head": head,
            "dirty": bool(files),
            "dirty_summary": {
                "staged": len(staged),
                "unstaged": len(unstaged),
                "untracked": len(untracked),
                "files": files,
            },
        },
    }


def add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit structured JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context = subparsers.add_parser("context", help="show local repository context")
    add_json_option(context)

    doctor = subparsers.add_parser("doctor", help="diagnose local workflow tooling")
    add_json_option(doctor)

    check_changed = subparsers.add_parser(
        "check-changed", help="select checks for changed paths"
    )
    check_changed.add_argument("base", nargs="?")
    add_json_option(check_changed)

    task_new = subparsers.add_parser("task-new", help="create local task state")
    task_new.add_argument("id")

    task_resume = subparsers.add_parser("task-resume", help="inspect task state and drift")
    task_resume.add_argument("id")
    add_json_option(task_resume)

    task_checkpoint = subparsers.add_parser(
        "task-checkpoint", help="persist a validated task checkpoint"
    )
    task_checkpoint.add_argument("id")

    task_export = subparsers.add_parser("task-export", help="export a sanitized handoff")
    task_export.add_argument("id")

    status = subparsers.add_parser("status", help="run read-only live diagnostics")
    status.add_argument("target", choices=("cluster", "network"))
    add_json_option(status)

    subparsers.add_parser("check", help="run full offline validation")
    subparsers.add_parser("fmt", help="format supported repository files")
    subparsers.add_parser("fmt-check", help="check formatting without mutation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "context":
        try:
            payload = context_payload()
        except RuntimeError as error:
            parser.error(str(error))
        if arguments.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            repository = payload["repository"]
            assert isinstance(repository, dict)
            branch = repository["branch"] or "detached HEAD"
            print(f"Repository: {repository['root']}")
            print(f"Revision: {branch} at {repository['head']}")
            print(f"Dirty: {str(repository['dirty']).lower()}")
        return 0

    print(f"{arguments.command}: not implemented in this work package", file=sys.stderr)
    return UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
