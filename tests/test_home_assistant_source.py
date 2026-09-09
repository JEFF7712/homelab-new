from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.home_assistant.models import ResourceDocument
from scripts.home_assistant.source import (
    adopt_resources,
    load_source_tree,
    remove_resource,
    validate_key,
    write_resource_atomic,
)


class TestHomeAssistantSource(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "home-assistant" / "core").mkdir(parents=True)
        (self.root / "home-assistant" / "automations").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_key_validation(self) -> None:
        validate_key("valid_key-123")
        with self.assertRaises(ValueError):
            validate_key("../traversal")
        with self.assertRaises(ValueError):
            validate_key("key with spaces")
        with self.assertRaises(ValueError):
            validate_key("key/slash")

    def test_atomic_write_and_load(self) -> None:
        doc = ResourceDocument(
            kind="automation",
            key="morning_lights",
            desired={"alias": "Morning Lights", "trigger": [], "action": []},
        )
        written_path = write_resource_atomic(self.root, doc)
        self.assertTrue(written_path.is_file())

        tree = load_source_tree(self.root)
        self.assertIn("automation/morning_lights", tree)
        loaded = tree["automation/morning_lights"]
        self.assertEqual(loaded.desired["alias"], "Morning Lights")

    def test_selected_adopt_preserves_unselected(self) -> None:
        doc1 = ResourceDocument(
            kind="automation", key="auto_one", desired={"alias": "One"}
        )
        doc2 = ResourceDocument(
            kind="automation", key="auto_two", desired={"alias": "Two"}
        )

        # Initial write of auto_one
        write_resource_atomic(self.root, doc1)

        # Adopt only auto_two
        written = adopt_resources(
            self.root, [doc1, doc2], selected_keys={"automation/auto_two"}
        )
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0].stem, "auto_two")

        tree = load_source_tree(self.root)
        self.assertIn("automation/auto_one", tree)
        self.assertIn("automation/auto_two", tree)
        self.assertEqual(tree["automation/auto_one"].desired["alias"], "One")
        self.assertEqual(tree["automation/auto_two"].desired["alias"], "Two")

    def test_adoption_rollback_on_write_error(self) -> None:
        doc_good = ResourceDocument(
            kind="automation", key="good", desired={"alias": "Good"}
        )
        # Write good doc first
        orig_file = write_resource_atomic(self.root, doc_good)
        orig_content = orig_file.read_text(encoding="utf-8")

        # Create a document whose target cannot be written (simulate error)
        # by trying to adopt with an unhashable/invalid desired object during dump
        class BadObject:
            pass

        bad_doc = ResourceDocument(
            kind="automation", key="bad", desired={"bad": BadObject()}
        )
        modified_good_doc = ResourceDocument(
            kind="automation", key="good", desired={"alias": "Modified"}
        )

        with self.assertRaises(RuntimeError):
            adopt_resources(self.root, [modified_good_doc, bad_doc])

        # Verify orig_file was rolled back to orig_content!
        self.assertEqual(orig_file.read_text(encoding="utf-8"), orig_content)

    def test_remove_resource(self) -> None:
        doc = ResourceDocument(kind="automation", key="temp", desired={"alias": "Temp"})
        path = write_resource_atomic(self.root, doc)
        self.assertTrue(path.is_file())
        removed = remove_resource(self.root, "automation", "temp")
        self.assertTrue(removed)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
