import unittest
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from opnsense_reconciler.inventory import Credentials
from opnsense_reconciler.reconcile import (
    main,
    reconcile_bgp_neighbors,
    reconcile_interfaces,
    reconcile_kea_interfaces,
    resolve_vlan_devices,
    verify_bgp,
)


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

        def reconcile_kea(client: object, desired: set[str]) -> None:
            seen["kea_client"] = client
            seen["kea_interfaces"] = desired

        def reconcile_bgp(client: object, desired: list[dict[str, object]]) -> dict[str, int]:
            seen["bgp_client"] = client
            seen["bgp_neighbors"] = desired
            return {"10.0.30.11": 64512}

        def prove_bgp(client: object, peers: dict[str, int], routes: set[str]) -> object:
            seen["proof_peers"] = peers
            seen["proof_routes"] = routes

            @dataclass(frozen=True)
            class Proof:
                ready: bool = True

            return Proof()

        with TemporaryDirectory() as directory:
            root = Path(directory)
            assignments = root / "assignments.json"
            inventory = root / "inventory.json"
            kea_interfaces = root / "kea-interfaces.json"
            bgp_neighbors = root / "bgp-neighbors.json"
            bgp_expected_routes = root / "bgp-expected-routes.json"
            assignments.write_text('[{"parent":"igb0","tag":30}]')
            inventory.write_text('{"assignment_api_available":true}')
            kea_interfaces.write_text('["opt1","opt2"]')
            bgp_neighbors.write_text('[{"address":"10.0.30.11","remoteas":"64512"}]')
            bgp_expected_routes.write_text('["10.0.40.10/32"]')

            main(
                [
                    "--assignments",
                    str(assignments),
                    "--inventory",
                    str(inventory),
                    "--kea-interfaces",
                    str(kea_interfaces),
                    "--bgp-neighbors",
                    str(bgp_neighbors),
                    "--bgp-expected-routes",
                    str(bgp_expected_routes),
                ],
                environ={
                    "OPNSENSE_URL": "https://192.168.1.1",
                    "OPNSENSE_API_KEY": "api-key",
                    "OPNSENSE_API_SECRET": "api-secret",
                    "OPNSENSE_CA_FILE": "/tmp/opnsense-ca.pem",
                    "OPNSENSE_TLS_SERVER_NAME": "OPNsense.internal",
                },
                client_factory=client_factory,
                reconcile=reconcile,
                reconcile_kea=reconcile_kea,
                reconcile_bgp=reconcile_bgp,
                prove_bgp=prove_bgp,
            )

        self.assertEqual(seen["credentials"], Credentials("api-key", "api-secret"))
        self.assertEqual(seen["assignment_api_available"], True)
        self.assertEqual(seen["desired"], [{"parent": "igb0", "tag": 30}])
        self.assertEqual(seen["kea_interfaces"], {"opt1", "opt2"})
        self.assertEqual(seen["bgp_neighbors"], [{"address": "10.0.30.11", "remoteas": "64512"}])
        self.assertEqual(seen["proof_peers"], {"10.0.30.11": 64512})
        self.assertEqual(seen["proof_routes"], {"10.0.40.10/32"})

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

    def test_reconcile_kea_interfaces_updates_and_verifies_listener_set(self) -> None:
        class KeaClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, object | None]] = []
                self.reads = 0

            def get(self, path: str) -> object:
                self.calls.append(("GET", path, None))
                if path == "/api/kea/service/status":
                    return {"status": "running"}
                self.reads += 1
                selected = {"opt1"} if self.reads == 1 else {"opt1", "opt2", "opt3", "opt5"}
                return {
                    "dhcpv4": {
                        "general": {
                            "interfaces": {
                                name: {"selected": int(name in selected), "value": name}
                                for name in ("lan", "opt1", "opt2", "opt3", "opt5")
                            }
                        }
                    }
                }

            def post(self, path: str, payload: object) -> object:
                self.calls.append(("POST", path, payload))
                return {"result": "saved"}

        client = KeaClient()
        desired = {"opt1", "opt2", "opt3", "opt5"}

        reconcile_kea_interfaces(client, desired)

        self.assertIn(
            (
                "POST",
                "/api/kea/dhcpv4/set",
                {
                    "dhcpv4": {
                        "general": {
                            "enabled": "1",
                            "manual_config": "0",
                            "interfaces": "opt1,opt2,opt3,opt5",
                            "valid_lifetime": "4000",
                            "fwrules": "1",
                            "dhcp_socket_type": "raw",
                        }
                    }
                },
            ),
            client.calls,
        )
        self.assertIn(("POST", "/api/kea/service/reconfigure", {}), client.calls)

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

    def test_verify_bgp_reads_ipv4_unicast_peers_and_bare_host_routes(self) -> None:
        class BgpClient:
            def get(self, path: str) -> object:
                responses = {
                    "/api/quagga/service/status": {"status": "running"},
                    "/api/quagga/diagnostics/bgpsummary": {
                        "response": {
                            "ipv4Unicast": {
                                "peers": {
                                    "10.0.30.11": {"state": "Established", "remoteAs": 64512},
                                    "10.0.30.12": {"state": "Established", "remoteAs": 64512},
                                    "10.0.30.13": {"state": "Established", "remoteAs": 64512},
                                }
                            }
                        }
                    },
                    "/api/quagga/diagnostics/search_bgproute4": {"rows": [{"prefix": "10.0.40.10"}]},
                }
                return responses[path]

        result = verify_bgp(
            BgpClient(),
            expected_peers={"10.0.30.11": 64512, "10.0.30.12": 64512, "10.0.30.13": 64512},
            expected_routes={"10.0.40.10/32"},
        )

        self.assertTrue(result.ready)
        self.assertEqual(result.missing_peers, set())
        self.assertEqual(result.missing_routes, set())

    def test_bgp_expected_routes_stay_inside_lb_pool(self) -> None:
        import ipaddress

        path = Path(__file__).resolve().parents[1] / "opnsense_reconciler/bgp-expected-routes.json"
        expected = json.loads(path.read_text())
        pool = ipaddress.ip_network("10.0.40.0/24")

        self.assertIsInstance(expected, list)
        self.assertTrue(expected)
        for prefix in expected:
            with self.subTest(prefix=prefix):
                network = ipaddress.ip_network(prefix)
                self.assertEqual(network.prefixlen, 32)
                self.assertTrue(network.subnet_of(pool))
                self.assertIn(int(network.network_address) - int(pool.network_address), range(10, 20))


class BgpNeighborReconciliationTests(unittest.TestCase):
    def desired(self) -> list[dict[str, object]]:
        return [
            {
                "address": "10.0.30.11",
                "description": "cilium-homelab-01",
                "remoteas": "64512",
                "updatesource": "opt3",
                "nexthopself": "1",
                "enabled": "1",
            },
            {
                "address": "10.0.30.12",
                "description": "cilium-homelab-02",
                "remoteas": "64512",
                "updatesource": "opt3",
                "nexthopself": "1",
                "enabled": "1",
            },
        ]

    def test_noop_when_live_matches_desired(self) -> None:
        class BgpClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def get(self, path: str) -> object:
                self.calls.append(("GET", path))
                return {
                    "rows": [
                        {
                            "uuid": "uuid-11",
                            "address": "10.0.30.11",
                            "description": "cilium-homelab-01",
                            "remoteas": "64512",
                            "updatesource": "opt3",
                            "nexthopself": "1",
                            "enabled": "1",
                        },
                        {
                            "uuid": "uuid-12",
                            "address": "10.0.30.12",
                            "description": "cilium-homelab-02",
                            "remoteas": "64512",
                            "updatesource": "opt3",
                            "nexthopself": "1",
                            "enabled": "1",
                        },
                    ]
                }

            def post(self, path: str, payload: object) -> object:
                raise AssertionError(f"matching state must not write: {path}")

        client = BgpClient()

        peers = reconcile_bgp_neighbors(client, self.desired())

        self.assertEqual(peers, {"10.0.30.11": 64512, "10.0.30.12": 64512})
        self.assertEqual(
            client.calls,
            [("GET", "/api/quagga/bgp/search_neighbor"), ("GET", "/api/quagga/bgp/search_neighbor")],
        )

    def test_adds_missing_peer_reconfigures_and_verifies(self) -> None:
        class BgpClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, object | None]] = []
                self.reads = 0

            def get(self, path: str) -> object:
                self.calls.append(("GET", path, None))
                self.reads += 1
                rows = [
                    {
                        "uuid": "uuid-11",
                        "address": "10.0.30.11",
                        "description": "cilium-homelab-01",
                        "remoteas": "64512",
                        "updatesource": "opt3",
                        "nexthopself": "1",
                        "enabled": "1",
                    }
                ]
                if self.reads > 1:
                    rows.append(
                        {
                            "uuid": "uuid-12",
                            "address": "10.0.30.12",
                            "description": "cilium-homelab-02",
                            "remoteas": "64512",
                            "updatesource": "opt3",
                            "nexthopself": "1",
                            "enabled": "1",
                        }
                    )
                return {"rows": rows}

            def post(self, path: str, payload: object) -> object:
                self.calls.append(("POST", path, payload))
                return {"result": "saved"}

        client = BgpClient()

        reconcile_bgp_neighbors(client, self.desired())

        self.assertIn(
            (
                "POST",
                "/api/quagga/bgp/add_neighbor",
                {
                    "neighbor": {
                        "address": "10.0.30.12",
                        "description": "cilium-homelab-02",
                        "remoteas": "64512",
                        "updatesource": "opt3",
                        "nexthopself": "1",
                        "enabled": "1",
                    }
                },
            ),
            client.calls,
        )
        self.assertIn(("POST", "/api/quagga/service/reconfigure", {}), client.calls)

    def test_updates_drifted_remote_as_by_uuid(self) -> None:
        class BgpClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, object | None]] = []
                self.rows = [
                    {
                        "uuid": "uuid-11",
                        "address": "10.0.30.11",
                        "description": "cilium-homelab-01",
                        "remoteas": "64599",
                        "updatesource": "opt3",
                        "nexthopself": "1",
                        "enabled": "1",
                    },
                    {
                        "uuid": "uuid-12",
                        "address": "10.0.30.12",
                        "description": "cilium-homelab-02",
                        "remoteas": "64512",
                        "updatesource": "opt3",
                        "nexthopself": "1",
                        "enabled": "1",
                    },
                ]

            def get(self, path: str) -> object:
                self.calls.append(("GET", path, None))
                return {"rows": [dict(row) for row in self.rows]}

            def post(self, path: str, payload: object) -> object:
                self.calls.append(("POST", path, payload))
                uuid = path.rsplit("/", 1)[-1]
                neighbor = payload.get("neighbor") if isinstance(payload, dict) else None
                for row in self.rows:
                    if row["uuid"] == uuid and isinstance(neighbor, dict):
                        row.update(neighbor)
                return {"result": "saved"}

        client = BgpClient()

        reconcile_bgp_neighbors(client, self.desired())

        update = [call for call in client.calls if call[1] == "/api/quagga/bgp/set_neighbor/uuid-11"]
        self.assertEqual(len(update), 1)
        self.assertEqual(
            update[0][2],
            {
                "neighbor": {
                    "address": "10.0.30.11",
                    "description": "cilium-homelab-01",
                    "remoteas": "64512",
                    "updatesource": "opt3",
                    "nexthopself": "1",
                    "enabled": "1",
                }
            },
        )

    def test_refuses_unknown_live_peer_without_writing(self) -> None:
        class BgpClient:
            def get(self, path: str) -> object:
                return {
                    "rows": [
                        {
                            "uuid": "uuid-11",
                            "address": "10.0.30.11",
                            "description": "cilium-homelab-01",
                            "remoteas": "64512",
                            "updatesource": "opt3",
                            "nexthopself": "1",
                            "enabled": "1",
                        },
                        {
                            "uuid": "uuid-rogue",
                            "address": "10.0.30.99",
                            "description": "rogue",
                            "remoteas": "64512",
                            "updatesource": "opt3",
                            "nexthopself": "1",
                            "enabled": "1",
                        },
                    ]
                }

            def post(self, path: str, payload: object) -> object:
                raise AssertionError(f"unexpected peer must not be deleted automatically: {path}")

        with self.assertRaisesRegex(RuntimeError, "10.0.30.99"):
            reconcile_bgp_neighbors(client=BgpClient(), desired_neighbors=self.desired()[:1])

    def test_rejects_failed_store_result(self) -> None:
        class BgpClient:
            def get(self, path: str) -> object:
                return {"rows": []}

            def post(self, path: str, payload: object) -> object:
                return {"result": "failed", "validations": {"neighbor.remoteas": "invalid"}}

        with self.assertRaisesRegex(RuntimeError, "failed"):
            reconcile_bgp_neighbors(client=BgpClient(), desired_neighbors=self.desired()[:1])

    def test_rejects_duplicate_desired_addresses(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            reconcile_bgp_neighbors(client=FakeClient(), desired_neighbors=[self.desired()[0], self.desired()[0]])

    def test_bgp_neighbor_config_declares_three_cilium_peers(self) -> None:
        path = Path(__file__).resolve().parents[1] / "opnsense_reconciler/bgp-neighbors.json"
        neighbors = json.loads(path.read_text())

        self.assertEqual(
            {neighbor["address"] for neighbor in neighbors},
            {"10.0.30.11", "10.0.30.12", "10.0.30.13"},
        )
        for neighbor in neighbors:
            with self.subTest(address=neighbor.get("address")):
                self.assertEqual(neighbor["remoteas"], "64512")
                self.assertEqual(neighbor["updatesource"], "opt3")
                self.assertEqual(neighbor["nexthopself"], "1")
                self.assertEqual(neighbor["enabled"], "1")


if __name__ == "__main__":
    unittest.main()
