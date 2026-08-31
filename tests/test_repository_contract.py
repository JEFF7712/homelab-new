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


if __name__ == "__main__":
    unittest.main()
