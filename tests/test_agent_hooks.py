import json
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentHookTest(unittest.TestCase):
    def test_client_hook_configuration_is_valid_json(self) -> None:
        for path in (
            ".claude/settings.json",
            ".codex/hooks.json",
            ".cursor/hooks.json",
        ):
            self.assertIsInstance(json.loads((ROOT / path).read_text()), dict)

    def test_session_start_returns_client_valid_json_and_recursion_fails_open(
        self,
    ) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            input='{"session_id":"fixture","hook_event_name":"SessionStart"}',
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            set(json.loads(result.stdout)),
            {"hookSpecificOutput"},
        )
        self.assertEqual(
            json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"],
            "SessionStart",
        )
        cursor = subprocess.run(
            ["bash", str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            input='{"conversation_id":"fixture","hook_event_name":"sessionStart"}',
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cursor.returncode, 0, cursor.stderr)
        self.assertEqual(set(json.loads(cursor.stdout)), {"additional_context"})
        recursive = subprocess.run(
            ["bash", str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            env={**os.environ, "AGENT_HOOK_ACTIVE": "1"},
            input="{}",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(json.loads(recursive.stdout), {})

    def test_session_start_fails_open_for_malformed_input(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            input="not-json",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()
