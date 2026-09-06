from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .context import context_payload, render_context
from .redact import redact
from .tasks import TaskError, checkpoint_task, create_task, export_task, resume_task

UNAVAILABLE = 69


def add_json_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="emit structured JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    context = subparsers.add_parser("context", help="show local repository context")
    add_json_option(context)
    context.add_argument("--task")

    doctor = subparsers.add_parser("doctor", help="diagnose local workflow tooling")
    add_json_option(doctor)

    check_changed = subparsers.add_parser(
        "check-changed", help="select checks for changed paths"
    )
    check_changed.add_argument("base", nargs="?")
    add_json_option(check_changed)

    task_new = subparsers.add_parser("task-new", help="create local task state")
    task_new.add_argument("id")
    add_json_option(task_new)

    task_resume = subparsers.add_parser(
        "task-resume", help="inspect task state and drift"
    )
    task_resume.add_argument("id")
    add_json_option(task_resume)

    task_checkpoint = subparsers.add_parser(
        "task-checkpoint", help="persist a validated task checkpoint"
    )
    task_checkpoint.add_argument("id")
    add_json_option(task_checkpoint)

    task_export = subparsers.add_parser(
        "task-export", help="export a sanitized handoff"
    )
    task_export.add_argument("id")
    task_export.add_argument("--replace", action="store_true")

    status = subparsers.add_parser("status", help="run read-only live diagnostics")
    status.add_argument("target", choices=("cluster", "network"))
    add_json_option(status)

    subparsers.add_parser("check", help="run full offline validation")
    subparsers.add_parser("fmt", help="format supported repository files")
    subparsers.add_parser("fmt-check", help="check formatting without mutation")
    return parser


def _read_json_stdin() -> dict[str, object]:
    try:
        value = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        raise TaskError("invalid JSON on stdin") from error
    if not isinstance(value, dict):
        raise TaskError("JSON stdin must contain an object")
    return value


def _print_task_result(operation: dict[str, object], structured: bool) -> None:
    if structured:
        print(json.dumps(operation, sort_keys=True))
    else:
        task = operation["task"]
        assert isinstance(task, dict)
        warning = operation.get("durability_warning")
        suffix = f" with warning: {warning}" if warning else ""
        print(
            f"Task {task['task_id']} revision {task['record_revision']} saved{suffix}"
        )


def _task_error_payload(command: str, error: BaseException) -> dict[str, object]:
    return {
        "schema_version": 1,
        "command": command,
        "status": "error",
        "error_type": type(error).__name__,
        "message": redact(str(error)),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "context":
        try:
            payload = context_payload(task_id=arguments.task)
        except (TaskError, RuntimeError, OSError) as error:
            print(f"context: {redact(str(error))}", file=sys.stderr)
            return 2
        if arguments.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(render_context(payload), end="")
        return 0

    if arguments.command == "task-export":
        try:
            path = export_task(Path.cwd(), arguments.id, replace=arguments.replace)
            print(path)
            return 0
        except (TaskError, RuntimeError, OSError) as error:
            print(f"task-export: {redact(str(error))}", file=sys.stderr)
            return 2

    if arguments.command in {"task-new", "task-checkpoint", "task-resume"}:
        try:
            if arguments.command == "task-new":
                _print_task_result(
                    create_task(Path.cwd(), arguments.id, _read_json_stdin()),
                    arguments.json,
                )
            elif arguments.command == "task-checkpoint":
                _print_task_result(
                    checkpoint_task(Path.cwd(), arguments.id, _read_json_stdin()),
                    arguments.json,
                )
            else:
                payload = resume_task(Path.cwd(), arguments.id)
                if arguments.json:
                    print(json.dumps(payload, sort_keys=True))
                else:
                    checkpoint = payload["checkpoint"]
                    assert isinstance(checkpoint, dict)
                    print(f"Task {arguments.id}: next action: {payload['next_action']}")
                    print(
                        f"Drift: head={str(checkpoint['head_drift']).lower()} fingerprint={str(checkpoint['fingerprint_drift']).lower()}"
                    )
            return 0
        except (TaskError, RuntimeError, OSError) as error:
            if arguments.json:
                print(
                    json.dumps(
                        _task_error_payload(arguments.command, error), sort_keys=True
                    )
                )
            else:
                print(f"{arguments.command}: {redact(str(error))}", file=sys.stderr)
            return 2

    print(f"{arguments.command}: not implemented in this work package", file=sys.stderr)
    return UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
