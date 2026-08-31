import unittest

from opnsense_reconciler.reconcile import reconcile_interfaces, verify_bgp


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str) -> object:
        raise AssertionError(f"unexpected read: {path}")

    def post(self, path: str, payload: object) -> object:
        raise AssertionError(f"unexpected write: {path}")


class ReconcileInterfaceTests(unittest.TestCase):
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

    def test_reconcile_interfaces_adds_one_explicit_static_ipv4_assignment(self) -> None:
        class AssignmentClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, object | None]] = []

            def get(self, path: str) -> object:
                self.calls.append(("GET", path, None))
                return {"rows": []}

            def post(self, path: str, payload: object) -> object:
                self.calls.append(("POST", path, payload))
                return {"result": "saved"}

        client = AssignmentClient()
        desired = {
            "descr": "management",
            "disablevlanhwfilter": "0",
            "enable": "1",
            "if": "vlan10",
            "ipaddr": "10.0.10.1/24",
            "lock": "1",
            "type4": "staticv4",
            "type6": "none",
            "dhcp6-ia-pd-len": "0",
        }

        reconcile_interfaces(client, True, [desired])

        self.assertEqual(
            client.calls,
            [
                ("GET", "/api/interfaces/assignment/search_item", None),
                ("POST", "/api/interfaces/assignment/add_item", {"interface": desired}),
                ("POST", "/api/interfaces/assignment/reconfigure", {}),
            ],
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
