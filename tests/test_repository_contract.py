from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_repository_has_required_documents(self) -> None:
        for relative_path in (
            ".gitignore",
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


if __name__ == "__main__":
    unittest.main()
