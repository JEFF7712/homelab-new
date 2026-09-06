from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = (
    "context",
    "doctor",
    "check-changed",
    "task-new",
    "task-resume",
    "task-checkpoint",
    "task-export",
    "status",
)
JSON_COMMANDS = ("context", "doctor", "check-changed", "task-resume", "status")


def run_agent(
    *arguments: str, cwd: Path = REPOSITORY_ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "scripts.agent", *arguments],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )


class AgentCliTest(unittest.TestCase):
    def test_help_lists_public_commands(self) -> None:
        result = run_agent("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in COMMANDS:
            self.assertIn(command, result.stdout)

    def test_structured_commands_accept_json_option(self) -> None:
        for command in JSON_COMMANDS:
            with self.subTest(command=command):
                result = run_agent(command, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--json", result.stdout)

    def test_context_json_reports_git_checkout_and_untracked_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent cli repo ") as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "-q", "-b", "main"], cwd=repository, check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Agent Test"], cwd=repository, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "agent-test@example.invalid"],
                cwd=repository,
                check=True,
            )
            (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "initial"], cwd=repository, check=True
            )
            (repository / "tracked.txt").write_text("modified\n", encoding="utf-8")
            (repository / "new file.txt").write_text("untracked\n", encoding="utf-8")

            result = run_agent("context", "--json", cwd=repository)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "context")
        self.assertEqual(payload["repository"]["root"], str(repository.resolve()))
        self.assertEqual(payload["repository"]["branch"], "main")
        self.assertFalse(payload["repository"]["detached"])
        self.assertRegex(payload["repository"]["head"], r"^[0-9a-f]{40}$")
        self.assertTrue(payload["repository"]["dirty"])
        self.assertEqual(payload["repository"]["dirty_summary"]["unstaged"], 1)
        self.assertEqual(payload["repository"]["dirty_summary"]["untracked"], 1)
        self.assertIn("new file.txt", payload["repository"]["dirty_summary"]["files"])

    def test_context_json_reports_detached_head(self) -> None:
        with tempfile.TemporaryDirectory(prefix="agent-detached-") as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "-q", "-b", "main"], cwd=repository, check=True
            )
            subprocess.run(
                ["git", "config", "user.name", "Agent Test"], cwd=repository, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "agent-test@example.invalid"],
                cwd=repository,
                check=True,
            )
            (repository / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "initial"], cwd=repository, check=True
            )
            subprocess.run(
                ["git", "checkout", "--detach", "-q"], cwd=repository, check=True
            )

            result = run_agent("context", "--json", cwd=repository)

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertIsNone(payload["repository"]["branch"])
        self.assertTrue(payload["repository"]["detached"])

    def test_unknown_command_exits_two_without_traceback(self) -> None:
        result = run_agent("does-not-exist")

        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_unimplemented_command_fails_honestly(self) -> None:
        result = run_agent("doctor")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not implemented", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
