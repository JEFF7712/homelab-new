"""Helper export must use effective registry names.

HA stores a helper's configured name/icon in the entity registry's
``original_name``/``original_icon`` fields; ``name``/``icon`` are only set
when a per-entity override exists. Reading only the override fields reports
phantoms drifts for correctly configured helpers.
"""

import unittest

from scripts.home_assistant.adapters.helper import HelperAdapter
from scripts.home_assistant.client import MockHomeAssistantClient


class HelperExportTest(unittest.TestCase):
    def _export(self, entity: dict) -> dict:
        client = MockHomeAssistantClient()
        client.entities = [entity]
        docs = HelperAdapter().export_from_live(client)
        self.assertEqual(len(docs), 1)
        return docs[0].desired  # type: ignore[no-any-return]

    def test_original_name_used_when_no_override(self) -> None:
        desired = self._export(
            {
                "entity_id": "input_boolean.guest_mode",
                "name": None,
                "icon": None,
                "original_name": "Guest Mode",
                "original_icon": "mdi:account-multiple",
            }
        )
        self.assertEqual(
            desired,
            {
                "entity_id": "input_boolean.guest_mode",
                "name": "Guest Mode",
                "icon": "mdi:account-multiple",
            },
        )

    def test_override_wins_over_original(self) -> None:
        desired = self._export(
            {
                "entity_id": "input_boolean.guest_mode",
                "name": "Guests",
                "icon": "mdi:party-popper",
                "original_name": "Guest Mode",
                "original_icon": "mdi:account-multiple",
            }
        )
        self.assertEqual(desired["name"], "Guests")
        self.assertEqual(desired["icon"], "mdi:party-popper")


if __name__ == "__main__":
    unittest.main()
