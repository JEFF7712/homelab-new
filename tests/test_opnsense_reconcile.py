import unittest

from opnsense_reconciler.reconcile import reconcile_interfaces, verify_bgp


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []


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
