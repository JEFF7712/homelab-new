from __future__ import annotations

import json
import os
import re
import secrets
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Self

from .git_state import GitBaseError, collect_git_state

TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SCHEMA_VERSION = 1
_CREATION_FIELDS = frozenset(
    {
        "objective",
        "status",
        "acceptance_criteria",
        "owning_agent",
        "session",
        "owned_files",
        "decisions",
        "durable_record_links",
        "completed_work",
        "remaining_work",
        "unresolved_failures",
        "next_action",
        "verification_records",
    }
)
_RECORD_FIELDS = _CREATION_FIELDS | frozenset(
    {
        "schema_version",
        "record_revision",
        "task_id",
        "base_commit",
        "checkpoint_head",
        "timestamp",
        "dirty_fingerprint",
        "blocked_on",
    }
)


class TaskError(RuntimeError):
    pass


class TaskValidationError(TaskError):
    pass


class TaskConflictError(TaskError):
    pass


class TaskLockError(TaskError):
    pass


class TaskNotFoundError(TaskError):
    pass


def validate_task_id(task_id: str) -> str:
    if not TASK_ID_PATTERN.fullmatch(task_id) or task_id in {".", ".."}:
        raise TaskValidationError("task id must match ^[a-z0-9][a-z0-9._-]{0,63}$")
    if Path(task_id).is_absolute() or "/" in task_id or "\\" in task_id:
        raise TaskValidationError("task id must not contain a path separator")
    return task_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_string(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise TaskValidationError(f"{field} is required and must be nonempty")
    return value


def _require_strings(record: Mapping[str, Any], field: str) -> list[str]:
    value = record.get(field)
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise TaskValidationError(
            f"{field} is required and must be a list of nonempty strings"
        )
    return value


def _validate_criteria(record: Mapping[str, Any]) -> None:
    criteria = record.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise TaskValidationError(
            "acceptance_criteria is required and must be nonempty"
        )
    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise TaskValidationError("each acceptance criterion must be an object")
        description = criterion.get("description")
        satisfied = criterion.get("satisfied")
        evidence = criterion.get("evidence")
        if (
            not isinstance(description, str)
            or not description.strip()
            or not isinstance(satisfied, bool)
            or not isinstance(evidence, str)
        ):
            raise TaskValidationError(
                "each acceptance criterion requires description, satisfied, and evidence"
            )
        if satisfied and not evidence.strip():
            raise TaskValidationError("satisfied acceptance criteria require evidence")


def _validate_verifications(record: Mapping[str, Any]) -> None:
    entries = record.get("verification_records")
    if not isinstance(entries, list):
        raise TaskValidationError("verification_records is required and must be a list")
    for entry in entries:
        if not isinstance(entry, dict):
            raise TaskValidationError("each verification record must be an object")
        for field in ("command", "time", "source_fingerprint", "evidence_path"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise TaskValidationError(f"verification record {field} is required")
        if not isinstance(entry.get("exit_code"), int) or isinstance(
            entry["exit_code"], bool
        ):
            raise TaskValidationError(
                "verification record exit_code must be an integer"
            )
        if not isinstance(entry.get("stale"), bool):
            raise TaskValidationError("verification record stale must be boolean")


def validate_task_record(
    record: Mapping[str, Any], *, require_system: bool = True
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise TaskValidationError("task record must be a JSON object")
    required = _RECORD_FIELDS if require_system else _CREATION_FIELDS
    missing = sorted(required - set(record))
    if missing:
        raise TaskValidationError(
            f"required task fields are missing: {', '.join(missing)}"
        )
    allowed = _RECORD_FIELDS if require_system else _CREATION_FIELDS | {"blocked_on"}
    unexpected = sorted(set(record) - (allowed | {"expected_revision"}))
    if unexpected:
        raise TaskValidationError(f"unexpected task fields: {', '.join(unexpected)}")
    result = dict(record)
    _require_string(result, "objective")
    _require_string(result, "owning_agent")
    _require_string(result, "session")
    _require_string(result, "next_action")
    _require_strings(result, "owned_files")
    for field in (
        "decisions",
        "durable_record_links",
        "completed_work",
        "remaining_work",
        "unresolved_failures",
    ):
        _require_strings(result, field)
    _validate_criteria(result)
    _validate_verifications(result)
    if result.get("status") not in {"active", "blocked", "complete"}:
        raise TaskValidationError("status must be active, blocked, or complete")
    blocked_on = result.get("blocked_on", [])
    if not isinstance(blocked_on, list) or any(
        not isinstance(item, str) or not item.strip() for item in blocked_on
    ):
        raise TaskValidationError("blocked_on must be a list of nonempty dependencies")
    if result["status"] == "blocked" and not blocked_on:
        raise TaskValidationError(
            "blocked tasks require a concrete dependency in blocked_on"
        )
    if result["status"] == "complete":
        if result["unresolved_failures"]:
            raise TaskValidationError("complete tasks cannot have unresolved failures")
        if any(
            not criterion["satisfied"] for criterion in result["acceptance_criteria"]
        ):
            raise TaskValidationError(
                "complete tasks require every acceptance criterion to be satisfied"
            )
    if require_system:
        if result.get("schema_version") != SCHEMA_VERSION:
            raise TaskValidationError("schema_version must be 1")
        revision = result.get("record_revision")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise TaskValidationError("record_revision must be a positive integer")
        validate_task_id(_require_string(result, "task_id"))
        for field in (
            "base_commit",
            "checkpoint_head",
            "timestamp",
            "dirty_fingerprint",
        ):
            _require_string(result, field)
    return result


def _task_directory(root: Path, task_id: str) -> Path:
    validate_task_id(task_id)
    return root / ".agent-state" / "tasks" / task_id


def task_path(root: Path, task_id: str) -> Path:
    return _task_directory(root, task_id) / "task.json"


def _read_record(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise TaskNotFoundError("task record does not exist") from error
    except json.JSONDecodeError as error:
        raise TaskValidationError("stored task record is invalid JSON") from error
    return validate_task_record(data)


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(8)}.tmp")
    directory_fd: int | None = None
    try:
        encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
        with open(temporary, "xb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        os.fsync(directory_fd)
    finally:
        if directory_fd is not None:
            os.close(directory_fd)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class _TaskLock:
    def __init__(self, directory: Path, session: str, timeout: float = 0.0) -> None:
        self.path = directory / ".lock"
        self.session = session
        self.timeout = timeout
        self.token = secrets.token_hex(16)
        self.acquired = False

    def __enter__(self) -> Self:
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                descriptor = os.open(
                    self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
                )
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TaskLockError("task checkpoint is locked by another writer")
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
                continue
            payload = {
                "pid": os.getpid(),
                "session": self.session,
                "timestamp": _now(),
                "token": self.token,
            }
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            self.acquired = True
            return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        if not self.acquired:
            return
        try:
            owner = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return
        if owner.get("token") == self.token:
            self.path.unlink(missing_ok=True)


def create_task(
    root: Path, task_id: str, creation: Mapping[str, Any]
) -> dict[str, Any]:
    task_id = validate_task_id(task_id)
    draft = validate_task_record(creation, require_system=False)
    state = collect_git_state(root)
    if state.head is None:
        raise TaskValidationError("task creation requires a committed HEAD")
    directory = _task_directory(state.root, task_id)
    try:
        directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise TaskConflictError("task record already exists") from error
    record = {
        **draft,
        "schema_version": SCHEMA_VERSION,
        "record_revision": 1,
        "task_id": task_id,
        "base_commit": state.head,
        "checkpoint_head": state.head,
        "timestamp": _now(),
        "dirty_fingerprint": state.fingerprint,
        "blocked_on": draft.get("blocked_on", []),
    }
    record = validate_task_record(record)
    _atomic_write_json(directory / "task.json", record)
    return record


def checkpoint_task(
    root: Path,
    task_id: str,
    checkpoint: Mapping[str, Any],
    *,
    lock_timeout: float = 0.0,
) -> dict[str, Any]:
    task_id = validate_task_id(task_id)
    if not isinstance(checkpoint, Mapping):
        raise TaskValidationError("checkpoint must be a JSON object")
    expected = checkpoint.get("expected_revision")
    if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
        raise TaskValidationError("expected_revision must be a positive integer")
    proposed = dict(checkpoint)
    proposed.pop("expected_revision")
    proposed = validate_task_record(proposed)
    if proposed["task_id"] != task_id:
        raise TaskValidationError("checkpoint task_id does not match command task id")
    state = collect_git_state(root)
    directory = _task_directory(state.root, task_id)
    path = directory / "task.json"
    with _TaskLock(directory, proposed["session"], lock_timeout):
        current = _read_record(path)
        if current["record_revision"] != expected:
            raise TaskConflictError(
                "revision conflict: reload the task record before checkpointing"
            )
        updated = {
            **proposed,
            "record_revision": expected + 1,
            "checkpoint_head": state.head or "unborn",
            "timestamp": _now(),
            "dirty_fingerprint": state.fingerprint,
        }
        updated = validate_task_record(updated)
        _atomic_write_json(path, updated)
    return updated


def resume_task(root: Path, task_id: str) -> dict[str, Any]:
    task_id = validate_task_id(task_id)
    root_state = collect_git_state(root)
    record = _read_record(task_path(root_state.root, task_id))
    try:
        state = collect_git_state(root_state.root, base=record["base_commit"])
        base_available = state.base.available
    except GitBaseError:
        state = root_state
        base_available = False
    stale_verifications = [
        {
            **verification,
            "stale": verification["source_fingerprint"] != state.fingerprint,
        }
        for verification in record["verification_records"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "task": record,
        "base": {"commit": record["base_commit"], "available": base_available},
        "checkpoint": {
            "recorded_head": record["checkpoint_head"],
            "current_head": state.head,
            "head_drift": record["checkpoint_head"] != state.head,
            "recorded_fingerprint": record["dirty_fingerprint"],
            "current_fingerprint": state.fingerprint,
            "fingerprint_drift": record["dirty_fingerprint"] != state.fingerprint,
        },
        "verifications": stale_verifications,
        "next_action": record["next_action"],
    }
