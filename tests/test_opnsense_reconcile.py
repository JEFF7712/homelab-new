import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from opnsense_reconciler.inventory import Credentials
from opnsense_reconciler.reconcile import main, reconcile_interfaces, resolve_vlan_devices, verify_bgp


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str) -> object:
        raise AssertionError(f"unexpected read: {path}")

    def post(self, path: str, payload: object) -> object:
        raise AssertionError(f"unexpected write: {path}")


class ReconcileInterfaceTests(unittest.TestCase):
    def test_main_loads_protected_environment_and_desired_assignments(self) -> None:
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

        def reconcile(client: object, assignment_api_available: bool, desired: list[dict[str, object]]) -> None:
            seen["client"] = client
            seen["assignment_api_available"] = assignment_api_available
            seen["desired"] = desired

        with TemporaryDirectory() as directory:
            root = Path(directory)
            assignments = root / "assignments.json"
            inventory = root / "inventory.json"
            assignments.write_text('[{"parent":"igb0","tag":30}]')
            inventory.write_text('{"assignment_api_available":true}')

            main(
                ["--assignments", str(assignments), "--inventory", str(inventory)],
                environ={
                    "OPNSENSE_URL": "https://192.168.1.1",
                    "OPNSENSE_API_KEY": "api-key",
                    "OPNSENSE_API_SECRET": "api-secret",
                    "OPNSENSE_CA_FILE": "/tmp/opnsense-ca.pem",
                    "OPNSENSE_TLS_SERVER_NAME": "OPNsense.internal",
                },
                client_factory=client_factory,
                reconcile=reconcile,
            )

        self.assertEqual(seen["credentials"], Credentials("api-key", "api-secret"))
        self.assertEqual(seen["assignment_api_available"], True)
        self.assertEqual(seen["desired"], [{"parent": "igb0", "tag": 30}])

    def test_resolve_vlan_devices_uses_live_parent_and_tag(self) -> None:
        desired = [{"descr": "clients", "parent": "igb0", "tag": 20, "ipaddr": "10.0.20.1/24"}]
        live_vlans = {
            "rows": [
                {
                    "if": "igb0",
                    "tag": "20",
                    "vlanif": "vlan01 [CLUSTER]",
                }
            ]
        }

        resolved = resolve_vlan_devices(desired, live_vlans)

        self.assertEqual(
            resolved,
            [{"descr": "clients", "if": "vlan01", "ipaddr": "10.0.20.1/24"}],
        )

    def test_resolve_vlan_devices_refuses_missing_tag(self) -> None:
        desired = [{"descr": "infrastructure", "parent": "igb0", "tag": 30}]

        with self.assertRaisesRegex(RuntimeError, "igb0 tag 30"):
            resolve_vlan_devices(desired, {"rows": []})

    def test_reconcile_interfaces_refuses_unavailable_assignment_api(self) -> None:
        client = FakeClient()

        with self.assertRaisesRegex(RuntimeError, "assignment API unavailable"):
            reconcile_interfaces(
                client=client,
                assignment_api_available=False,
                desired_interfaces=[],
            )

        self.assertEqual(client.calls, [])

    def test_reconcile_interfaces_reads_current_assignments_before_noop(self) -> None:
        class AssignmentClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def get(self, path: str) -> object:
                self.calls.append(("GET", path))
                return {"rows": []}

            def post(self, path: str, payload: object) -> object:
                raise AssertionError("no-op reconciliation must not write")

        client = AssignmentClient()

        reconcile_interfaces(
            client=client,
            assignment_api_available=True,
            desired_interfaces=[],
        )

        self.assertEqual(client.calls, [("GET", "/api/interfaces/assignment/search_item")])

    def test_reconcile_interfaces_adds_assignment_and_verifies_runtime(self) -> None:
        class AssignmentClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, object | None]] = []

            def get(self, path: str) -> object:
                self.calls.append(("GET", path, None))
                if path == "/api/interfaces/vlan_settings/search_item":
                    return {"rows": [{"if": "igb0", "tag": "10", "vlanif": "vlan02 [management]"}]}
                if path == "/api/interfaces/assignment/search_item":
                    return {"rows": []}
                if path == "/api/interfaces/overview/interfaces_info/true":
                    return {
                        "rows": [{"device": "vlan02", "addr4": "10.0.10.1/24", "description": "management"}]
                    }
                raise AssertionError(f"unexpected read: {path}")

            def post(self, path: str, payload: object) -> object:
                self.calls.append(("POST", path, payload))
                return {"result": "saved"}

        client = AssignmentClient()
        desired = {
            "descr": "management",
            "disablevlanhwfilter": "0",
            "enable": "1",
            "ipaddr": "10.0.10.1/24",
            "lock": "1",
            "parent": "igb0",
            "tag": 10,
            "type4": "staticv4",
            "type6": "none",
            "dhcp6-ia-pd-len": "0",
        }

        reconcile_interfaces(client, True, [desired])
        resolved_desired = {key: value for key, value in desired.items() if key not in {"parent", "tag"}}
        resolved_desired["if"] = "vlan02"

        self.assertEqual(
            client.calls,
            [
                ("GET", "/api/interfaces/vlan_settings/search_item", None),
                ("GET", "/api/interfaces/assignment/search_item", None),
                (
                    "POST",
                    "/api/interfaces/assignment/add_item",
                    {"interface": resolved_desired},
                ),
                ("POST", "/api/interfaces/assignment/reconfigure", {}),
                ("GET", "/api/interfaces/overview/interfaces_info/true", None),
            ],
        )

    def test_reconcile_interfaces_refuses_static_l3_runtime_drift(self) -> None:
        class DriftClient:
            def get(self, path: str) -> object:
                responses = {
                    "/api/interfaces/vlan_settings/search_item": {
                        "rows": [{"if": "igb0", "tag": "10", "vlanif": "vlan02 [management]"}]
                    },
                    "/api/interfaces/assignment/search_item": {
                        "rows": [{"if": "vlan02", "identifier": "opt2"}]
                    },
                    "/api/interfaces/overview/interfaces_info/true": {
                        "rows": [{"device": "vlan02", "addr4": None, "description": "management"}]
                    },
                }
                return responses[path]

            def post(self, path: str, payload: object) -> object:
                raise AssertionError(f"runtime drift must not invoke unsupported write: {path}")

        desired = [{"parent": "igb0", "tag": 10, "descr": "management", "ipaddr": "10.0.10.1/24"}]

        with self.assertRaisesRegex(RuntimeError, "OPNsense 26.7 assignment API cannot configure"):
            reconcile_interfaces(DriftClient(), True, desired)

    def test_assignment_config_declares_all_vlan_gateways(self) -> None:
        path = Path(__file__).resolve().parents[1] / "opnsense_reconciler/assignments.json"
        assignments = json.loads(path.read_text())

        self.assertEqual(
            {(assignment["parent"], assignment["tag"]) for assignment in assignments},
            {("igb0", 10), ("igb0", 20), ("igb0", 30), ("igb0", 40), ("igb0", 50), ("igb0", 60)},
        )
        self.assertEqual(
            {assignment["ipaddr"] for assignment in assignments},
            {
                "10.0.10.1/24",
                "10.0.20.1/24",
                "10.0.30.1/24",
                "10.0.40.1/24",
                "10.0.50.1/24",
                "10.0.60.1/24",
            },
        )


class BgpVerificationTests(unittest.TestCase):
    def test_verify_bgp_reports_missing_canary_route(self) -> None:
        class BgpClient:
            def get(self, path: str) -> object:
                responses = {
                    "/api/quagga/service/status": {"status": "running"},
                    "/api/quagga/diagnostics/bgpsummary": {
                        "response": {"peers": {"10.0.30.11": {"state": "Established", "remoteAs": 64512}}}
                    },
                    "/api/quagga/diagnostics/search_bgproute4": {"rows": []},
                }
                return responses[path]

        result = verify_bgp(
            BgpClient(),
            expected_peers={"10.0.30.11": 64512},
            expected_routes={"10.0.40.10/32"},
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.missing_routes, {"10.0.40.10/32"})


if __name__ == "__main__":
    unittest.main()
