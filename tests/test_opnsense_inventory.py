import unittest

from opnsense_reconciler.inventory import collect_inventory, parse_credentials


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str) -> object:
        self.calls.append(("GET", path))
        responses: dict[str, object] = {
            "/api/core/backup/providers": {"rows": [{"id": "this"}]},
            "/api/core/backup/backups/this": {"rows": [{"id": "backup-1"}]},
            "/api/core/backup/download/this/backup-1": "<config />",
            "/api/interfaces/overview/interfaces_info/true": {"interfaces": {}},
            "/api/interfaces/vlan_settings/search_item": {"rows": []},
            "/api/interfaces/assignment/search_item": {"rows": []},
        }
        return responses[path]


class InventoryTests(unittest.TestCase):
    def test_parse_credentials_reads_labelled_key_and_secret(self) -> None:
        credentials = parse_credentials("key: api-key\nsecret: api-secret\n")

        self.assertEqual(credentials.key, "api-key")
        self.assertEqual(credentials.secret, "api-secret")

    def test_collect_inventory_uses_get_only_and_detects_assignment_api(self) -> None:
        client = FakeClient()

        inventory = collect_inventory(client)

        self.assertTrue(inventory.assignment_api_available)
        self.assertEqual(inventory.backup_provider, "this")
        self.assertEqual(inventory.backup_id, "backup-1")
        self.assertEqual(
            client.calls,
            [
                ("GET", "/api/core/backup/providers"),
                ("GET", "/api/core/backup/backups/this"),
                ("GET", "/api/core/backup/download/this/backup-1"),
                ("GET", "/api/interfaces/overview/interfaces_info/true"),
                ("GET", "/api/interfaces/vlan_settings/search_item"),
                ("GET", "/api/interfaces/assignment/search_item"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
