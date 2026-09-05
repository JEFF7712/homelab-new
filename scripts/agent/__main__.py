from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .git_state import collect_git_state


UNAVAILABLE = 69


def context_payload() -> dict[str, object]:
    state = collect_git_state()
    return {
        "schema_version": 1,
        "command": "context",
        "repository": {
            "root": str(state.root),
            "branch": state.branch,
            "detached": state.detached,
            "head": state.head,
            "dirty": state.dirty,
            "dirty_summary": {
                "staged": state.counts.staged,
                "unstaged": state.counts.unstaged,
                "untracked": state.counts.untracked,
                "files": list(state.affected_paths),
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
