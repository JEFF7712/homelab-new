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

    def test_session_start_returns_json_and_recursion_fails_open(self) -> None:
        result = subprocess.run(
            [str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            input='{"session_id":"fixture"}',
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsInstance(json.loads(result.stdout), dict)
        recursive = subprocess.run(
            [str(ROOT / "hooks/session-start")],
            cwd=ROOT,
            env={**os.environ, "AGENT_HOOK_ACTIVE": "1"},
            input="{}",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(json.loads(recursive.stdout), {})


if __name__ == "__main__":
    unittest.main()
