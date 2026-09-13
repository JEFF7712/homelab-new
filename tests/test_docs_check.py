from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.checks.docs import iter_markdown_files, trailing_whitespace_errors


class DocsCheckTest(unittest.TestCase):
    def test_vendored_trees_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "docs").mkdir()
            (root / "docs" / "owned.md").write_text("clean\n", encoding="utf-8")
            vendored = root / ".opencode" / "node_modules" / "dep"
            vendored.mkdir(parents=True)
            (vendored / "README.md").write_text("dirty   \n", encoding="utf-8")

            errors = trailing_whitespace_errors(root)
            scanned = list(iter_markdown_files(root))

        self.assertEqual(errors, [])
        self.assertEqual(scanned, [root / "docs" / "owned.md"])

    def test_owned_trailing_whitespace_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "notes.md").write_text("dirty   \n", encoding="utf-8")

            errors = trailing_whitespace_errors(root)

        self.assertEqual(len(errors), 1)
        self.assertIn("notes.md:1: trailing whitespace", errors[0])


if __name__ == "__main__":
    unittest.main()
