from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.agent_helpers import commit, make_repository

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def creation_payload() -> dict[str, object]:
    return {
        "objective": "Persist a safe checkpoint",
        "status": "active",
        "acceptance_criteria": [
            {"description": "state is durable", "satisfied": False, "evidence": ""}
        ],
        "owning_agent": "codex",
        "session": "session-1",
        "owned_files": ["scripts/agent/tasks.py"],
        "decisions": [],
        "durable_record_links": [],
        "completed_work": [],
        "remaining_work": ["write state"],
        "unresolved_failures": [],
        "next_action": "write state",
        "verification_records": [],
    }


def run_agent(
    repository: Path, *arguments: str, document: object | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.agent", *arguments],
        cwd=repository,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
        input=None if document is None else json.dumps(document),
        text=True,
        capture_output=True,
        check=False,
    )


class TaskRecordTest(unittest.TestCase):
    def test_task_id_validation_rejects_unsafe_values(self) -> None:
        from scripts.agent.tasks import TaskValidationError, validate_task_id

        self.assertEqual(validate_task_id("safe.task_1-a"), "safe.task_1-a")
        for task_id in ("", ".", "..", "UPPER", "a/child", "/absolute", "a" * 65):
            with self.subTest(task_id=task_id), self.assertRaises(TaskValidationError):
                validate_task_id(task_id)

    def test_create_refuses_overwrite_and_records_checkout_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            first = run_agent(
                repository, "task-new", "state", document=creation_payload()
            )
            second = run_agent(
                repository, "task-new", "state", document=creation_payload()
            )
            record = json.loads(
                (repository / ".agent-state/tasks/state/task.json").read_text()
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists", second.stderr)
            self.assertEqual(record["schema_version"], 1)
            self.assertEqual(record["record_revision"], 1)
            self.assertEqual(record["task_id"], "state")
            self.assertRegex(record["base_commit"], r"^[0-9a-f]{40}$")
            self.assertEqual(record["base_commit"], record["checkpoint_head"])
            self.assertRegex(record["dirty_fingerprint"], r"^[0-9a-f]{64}$")

    def test_creation_requires_complete_metadata_and_stdin_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            missing = run_agent(
                repository, "task-new", "state", document={"objective": "x"}
            )
            invalid = subprocess.run(
                [sys.executable, "-m", "scripts.agent", "task-new", "state"],
                cwd=repository,
                env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
                input="{bad",
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("required", missing.stderr)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("invalid JSON", invalid.stderr)
        self.assertNotIn("Traceback", invalid.stderr)

    def test_creation_allows_blocked_task_with_concrete_dependency(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            payload = {
                **creation_payload(),
                "status": "blocked",
                "blocked_on": ["review from owner"],
            }
            result = run_agent(repository, "task-new", "state", document=payload)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_checkpoint_requires_matching_revision_and_preserves_previous_record(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            self.assertEqual(
                run_agent(
                    repository, "task-new", "state", document=creation_payload()
                ).returncode,
                0,
            )
            path = repository / ".agent-state/tasks/state/task.json"
            record = json.loads(path.read_text())
            update = {**record, "expected_revision": 1, "next_action": "run tests"}
            first = run_agent(repository, "task-checkpoint", "state", document=update)
            second = run_agent(repository, "task-checkpoint", "state", document=update)
            persisted = json.loads(path.read_text())

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("revision conflict", second.stderr)
        self.assertEqual(persisted["record_revision"], 2)
        self.assertEqual(persisted["next_action"], "run tests")

    def test_checkpoint_rejects_blocked_without_dependency_and_incomplete_complete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            self.assertEqual(
                run_agent(
                    repository, "task-new", "state", document=creation_payload()
                ).returncode,
                0,
            )
            path = repository / ".agent-state/tasks/state/task.json"
            before = path.read_text()
            record = json.loads(before)
            blocked = run_agent(
                repository,
                "task-checkpoint",
                "state",
                document={**record, "expected_revision": 1, "status": "blocked"},
            )
            complete = run_agent(
                repository,
                "task-checkpoint",
                "state",
                document={**record, "expected_revision": 1, "status": "complete"},
            )
            persisted = path.read_text()

        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("dependency", blocked.stderr)
        self.assertNotEqual(complete.returncode, 0)
        self.assertIn("acceptance", complete.stderr)
        self.assertEqual(persisted, before)

    def test_lock_conflict_and_interrupted_replace_keep_valid_record(self) -> None:
        from scripts.agent.tasks import TaskLockError, checkpoint_task

        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            (repository / "tracked.txt").write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            self.assertEqual(
                run_agent(
                    repository, "task-new", "state", document=creation_payload()
                ).returncode,
                0,
            )
            path = repository / ".agent-state/tasks/state/task.json"
            before = path.read_text()
            record = json.loads(before)
            lock = path.parent / ".lock"
            lock.write_text('{"pid": 1}', encoding="utf-8")
            with self.assertRaises(TaskLockError):
                checkpoint_task(repository, "state", {**record, "expected_revision": 1})
            lock.unlink()
            with (
                mock.patch(
                    "scripts.agent.tasks.os.replace", side_effect=OSError("injected")
                ),
                self.assertRaises(OSError),
            ):
                checkpoint_task(repository, "state", {**record, "expected_revision": 1})
            persisted = path.read_text()

        self.assertEqual(persisted, before)

    def test_resume_reports_drift_unavailable_base_and_stale_verification_without_rewrite(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-task-") as directory:
            repository = make_repository(Path(directory))
            tracked = repository / "tracked.txt"
            tracked.write_text("initial\n", encoding="utf-8")
            commit(repository, "initial")
            payload = creation_payload()
            self.assertEqual(
                run_agent(repository, "task-new", "state", document=payload).returncode,
                0,
            )
            path = repository / ".agent-state/tasks/state/task.json"
            record = json.loads(path.read_text())
            record["verification_records"] = [
                {
                    "command": "python -m unittest",
                    "exit_code": 0,
                    "time": record["timestamp"],
                    "source_fingerprint": record["dirty_fingerprint"],
                    "evidence_path": "evidence.txt",
                    "stale": False,
                }
            ]
            self.assertEqual(
                run_agent(
                    repository,
                    "task-checkpoint",
                    "state",
                    document={**record, "expected_revision": 1},
                ).returncode,
                0,
            )
            tracked.write_text("changed\n", encoding="utf-8")
            dirty = run_agent(repository, "task-resume", "state", "--json")
            commit(repository, "second")
            head = run_agent(repository, "task-resume", "state", "--json")
            latest = json.loads(path.read_text())
            latest["base_commit"] = "f" * 40
            path.write_text(json.dumps(latest), encoding="utf-8")
            unavailable = run_agent(repository, "task-resume", "state", "--json")

        dirty_payload = json.loads(dirty.stdout)
        head_payload = json.loads(head.stdout)
        unavailable_payload = json.loads(unavailable.stdout)
        self.assertTrue(dirty_payload["checkpoint"]["fingerprint_drift"])
        self.assertTrue(dirty_payload["verifications"][0]["stale"])
        self.assertTrue(head_payload["checkpoint"]["head_drift"])
        self.assertFalse(unavailable_payload["base"]["available"])
        self.assertIn("next_action", unavailable_payload)


class RedactionTest(unittest.TestCase):
    def test_redacts_secrets_headers_private_keys_environment_and_machine_paths(
        self,
    ) -> None:
        from scripts.agent.redact import redact

        value = redact(
            "token=abc123 password=hunter2 API_KEY=key-value Authorization: Bearer abc "
            "X-API-Key: header-key "
            "AWS_SECRET_ACCESS_KEY=xyz ~/.ssh/id_ed25519 ~/.config/sops/age/keys.txt "
            "/home/a/.kube/config -----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
        )

        for secret in (
            "abc123",
            "hunter2",
            "key-value",
            "Bearer abc",
            "header-key",
            "xyz",
            "id_ed25519",
            "keys.txt",
            "PRIVATE KEY",
        ):
            self.assertNotIn(secret, value)
        self.assertIn("[REDACTED]", value)
        self.assertEqual(redact("X-API-Key: header-key"), "X-API-Key: [REDACTED]")


if __name__ == "__main__":
    unittest.main()
