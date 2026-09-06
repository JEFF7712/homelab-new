import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from opnsense_reconciler.inventory import (
    Credentials,
    collect_inventory,
    collect_provider_inventory,
    main,
    parse_credentials,
    validate_api_path,
    write_inventory_artifacts,
)


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str) -> object:
        self.calls.append(("GET", path))
        responses: dict[str, object] = {
            "/api/core/backup/providers": {"items": {"this": {}}},
            "/api/core/backup/backups/this": {"rows": [{"id": "backup-1"}]},
            "/api/interfaces/overview/interfaces_info/true": {"interfaces": {}},
            "/api/interfaces/vlan_settings/search_item": {"rows": []},
            "/api/interfaces/assignment/search_item": {"rows": []},
        }
        return responses[path]

    def get_bytes(self, path: str) -> bytes:
        self.calls.append(("GET", path))
        if path != "/api/core/backup/download/this/backup-1":
            raise AssertionError(f"unexpected binary path: {path}")
        return b"<config />"


class AssignmentApiUnavailableClient(FakeClient):
    def get(self, path: str) -> object:
        if path == "/api/interfaces/assignment/search_item":
            self.calls.append(("GET", path))
            raise RuntimeError("OPNsense returned HTTP 404")
        return super().get(path)


class InventoryTests(unittest.TestCase):
    def test_client_rejects_non_api_path(self) -> None:
        with self.assertRaisesRegex(ValueError, "API path"):
            validate_api_path("/not-api")

    def test_parse_credentials_reads_labelled_key_and_secret(self) -> None:
        credentials = parse_credentials("key: api-key\nsecret: api-secret\n")

        self.assertEqual(credentials.key, "api-key")
        self.assertEqual(credentials.secret, "api-secret")

        credentials = parse_credentials("key = api-key\nsecret = api-secret\n")
        self.assertEqual(credentials.key, "api-key")
        self.assertEqual(credentials.secret, "api-secret")

    def test_collect_inventory_uses_get_only_and_detects_assignment_api(self) -> None:
        client = FakeClient()

        inventory = collect_inventory(client)

        self.assertTrue(inventory.assignment_api_available)
        self.assertEqual(inventory.backup_provider, "this")
        self.assertEqual(inventory.backup_id, "backup-1")
        self.assertEqual(inventory.backup, b"<config />")
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

    def test_collect_inventory_marks_unavailable_assignment_api_without_failing(
        self,
    ) -> None:
        client = AssignmentApiUnavailableClient()

        inventory = collect_inventory(client)

        self.assertFalse(inventory.assignment_api_available)
        self.assertIsNone(inventory.assignments)
        self.assertEqual(
            client.calls[-1], ("GET", "/api/interfaces/assignment/search_item")
        )

    def test_collect_inventory_accepts_backup_items_list(self) -> None:
        client = FakeClient()
        original_get = client.get

        def get(path: str) -> object:
            if path == "/api/core/backup/backups/this":
                client.calls.append(("GET", path))
                return {"items": [{"id": "backup-1"}]}
            return original_get(path)

        client.get = get  # type: ignore[method-assign]

        inventory = collect_inventory(client)

        self.assertEqual(inventory.backup_id, "backup-1")

    def test_write_inventory_artifacts_encrypts_backup_without_plaintext(self) -> None:
        inventory = collect_inventory(FakeClient())

        def encrypt(backup: bytes, recipient: str, destination: Path) -> None:
            self.assertEqual(backup, b"<config />")
            self.assertEqual(recipient, "age1example")
            destination.write_bytes(b"encrypted")

        with TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            write_inventory_artifacts(
                inventory, artifact_dir, "age1example", encrypt=encrypt
            )

            summary = json.loads((artifact_dir / "inventory.json").read_text())
            self.assertEqual(
                summary["backup_sha256"], hashlib.sha256(b"<config />").hexdigest()
            )
            self.assertTrue((artifact_dir / "config.xml.age").is_file())
            self.assertFalse((artifact_dir / "config.xml").exists())

    def test_main_uses_protected_ci_environment(self) -> None:
        seen: dict[str, object] = {}

        def client_factory(
            url: str,
            credentials: Credentials,
            ca_file: str,
            server_name: str | None,
        ) -> FakeClient:
            seen["url"] = url
            seen["credentials"] = credentials
            seen["ca_file"] = ca_file
            seen["server_name"] = server_name
            return FakeClient()

        def artifact_writer(
            inventory: object, artifact_dir: Path, recipient: str
        ) -> None:
            seen["artifact_dir"] = artifact_dir
            seen["recipient"] = recipient

        main(
            ["--artifact-dir", "/tmp/opnsense-evidence"],
            environ={
                "OPNSENSE_URL": "https://192.168.1.1",
                "OPNSENSE_API_KEY": "api-key",
                "OPNSENSE_API_SECRET": "api-secret",
                "OPNSENSE_CA_FILE": "/tmp/opnsense-ca.pem",
                "OPNSENSE_BACKUP_RECIPIENT": "age1example",
                "OPNSENSE_TLS_SERVER_NAME": "OPNsense.internal",
            },
            client_factory=client_factory,
            artifact_writer=artifact_writer,
        )

        self.assertEqual(seen["url"], "https://192.168.1.1")
        self.assertEqual(seen["credentials"], Credentials("api-key", "api-secret"))
        self.assertEqual(seen["ca_file"], "/tmp/opnsense-ca.pem")
        self.assertEqual(seen["server_name"], "OPNsense.internal")
        self.assertEqual(seen["artifact_dir"], Path("/tmp/opnsense-evidence"))
        self.assertEqual(seen["recipient"], "age1example")

    def test_collect_provider_inventory_reads_only_supported_resource_lists(
        self,
    ) -> None:
        class ProviderClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def get(self, path: str) -> object:
                self.calls.append(("GET", path))
                return {"rows": [{"uuid": f"uuid-{len(self.calls)}"}]}

        client = ProviderClient()

        inventory = collect_provider_inventory(client)

        self.assertEqual(inventory.vlan_ids, {"uuid-1"})
        self.assertEqual(inventory.dhcp_subnet_ids, {"uuid-2"})
        self.assertEqual(inventory.dhcp_reservation_ids, {"uuid-3"})
        self.assertEqual(inventory.firewall_filter_ids, {"uuid-4"})
        self.assertEqual(inventory.unbound_forward_ids, {"uuid-5"})
        self.assertEqual(
            client.calls,
            [
                ("GET", "/api/interfaces/vlan_settings/search_item"),
                ("GET", "/api/kea/dhcpv4/search_subnet"),
                ("GET", "/api/kea/dhcpv4/search_reservation"),
                ("GET", "/api/firewall/filter/search_rule"),
                ("GET", "/api/unbound/settings/search_forward"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
