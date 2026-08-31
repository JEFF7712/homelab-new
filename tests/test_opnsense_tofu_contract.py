from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OPNsenseTofuContractTests(unittest.TestCase):
    def test_network_declares_provider_managed_resource_types(self) -> None:
        network = (ROOT / "tofu/opnsense/network.tf").read_text()

        for resource_type in (
            "opnsense_interfaces_vlan",
            "opnsense_kea_dhcpv4_subnet",
            "opnsense_kea_dhcpv4_reservation",
            "opnsense_firewall_filter",
            "opnsense_unbound_settings",
            "opnsense_unbound_forward",
        ):
            with self.subTest(resource_type=resource_type):
                self.assertIn(resource_type, network)


if __name__ == "__main__":
    unittest.main()
