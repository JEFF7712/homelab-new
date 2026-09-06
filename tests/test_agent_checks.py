from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.agent.checks import select_checks
from scripts.agent.git_state import collect_git_state
from tests.agent_helpers import commit, make_repository


class AgentCheckSelectionTest(unittest.TestCase):
    def select(self, path: str):
        with tempfile.TemporaryDirectory() as directory:
            repository = make_repository(Path(directory))
            target = repository / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x\n")
            commit(repository, "initial")
            target.write_text("y\n")
            return select_checks(collect_git_state(repository))

    def test_routes_repository_surfaces_with_reasons(self) -> None:
        expected = {
            "flake/hosts/homelab-01/default.nix": "nix-host-homelab-01",
            "flake/modules/k3s-server.nix": "nix-all-hosts",
            "opnsense_reconciler/reconcile.py": "python",
            "gitops/platform/namespace.yaml": "gitops",
            "tofu/opnsense/network.tf": "tofu",
            "scripts/agent/context.py": "agent-workflows",
            "docs/readme.md": "docs",
            "unknown/code.go": "full",
            ".gitlab-ci.yml": "full",
        }
        for path, check in expected.items():
            with self.subTest(path=path):
                selection = self.select(path)
                self.assertIn(check, [item.name for item in selection.checks])
                self.assertTrue(all(item.reasons for item in selection.checks))

    def test_deduplicates_checks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = make_repository(Path(directory))
            for name in ("opnsense_reconciler/a.py", "opnsense_reconciler/b.py"):
                path = repository / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x")
            state = collect_git_state(repository)
            selection = select_checks(state)
        self.assertEqual([item.name for item in selection.checks].count("python"), 1)


if __name__ == "__main__":
    unittest.main()
