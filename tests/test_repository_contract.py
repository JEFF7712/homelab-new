from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_repository_has_required_documents(self) -> None:
        for relative_path in (
            ".gitignore",
            ".gitlab-ci.yml",
            "README.md",
            "docs/superpowers/specs/2026-08-30-nixos-homelab-rebuild-design.md",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_gitignore_excludes_private_material(self) -> None:
        gitignore = ROOT / ".gitignore"
        self.assertTrue(gitignore.is_file())
        ignored = gitignore.read_text()
        for pattern in ("secrets/keys/", "*.decrypted.yaml", ".direnv/", "result"):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, ignored)

    def test_ci_uses_the_repository_flake(self) -> None:
        pipeline_path = ROOT / ".gitlab-ci.yml"
        self.assertTrue(pipeline_path.is_file())
        pipeline = pipeline_path.read_text()
        self.assertIn("nix develop ./flake", pipeline)
        self.assertIn("nix flake check ./flake", pipeline)

    def test_opnsense_pipeline_requires_manual_main_apply(self) -> None:
        pipeline = (ROOT / ".gitlab-ci.yml").read_text()

        for job in ("opnsense_inventory:", "opnsense_plan:", "opnsense_apply:"):
            self.assertIn(job, pipeline)
        apply_block = pipeline.split("opnsense_apply:", maxsplit=1)[1]
        self.assertIn("when: manual", apply_block)
        self.assertIn('$CI_COMMIT_BRANCH == "main"', apply_block)
        self.assertIn("apply desired.tfplan", apply_block)
        self.assertIn("check_plan", apply_block)
        self.assertIn("python -m opnsense_reconciler.reconcile", apply_block)
        self.assertIn("--kea-interfaces opnsense_reconciler/kea-interfaces.json", apply_block)
        self.assertLess(
            apply_block.index("apply desired.tfplan"),
            apply_block.index("python -m opnsense_reconciler.reconcile"),
        )

    def test_opnsense_pipeline_uses_locked_gitlab_state(self) -> None:
        backend = (ROOT / "tofu/opnsense/backend.tf").read_text()
        pipeline = (ROOT / ".gitlab-ci.yml").read_text()

        self.assertIn('backend "http"', backend)
        for value in (
            "TF_STATE_NAME: opnsense-production",
            "TF_HTTP_ADDRESS:",
            "TF_HTTP_LOCK_ADDRESS:",
            "TF_HTTP_UNLOCK_ADDRESS:",
            "TF_HTTP_LOCK_METHOD: POST",
            "TF_HTTP_UNLOCK_METHOD: DELETE",
            "init -reconfigure",
        ):
            with self.subTest(value=value):
                self.assertIn(value, pipeline)
        self.assertNotIn("init -backend=false", pipeline)


if __name__ == "__main__":
    unittest.main()
