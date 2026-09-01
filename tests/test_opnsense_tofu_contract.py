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

    def test_existing_vlan_is_imported_without_forcing_device_name(self) -> None:
        imports = (ROOT / "tofu/opnsense/imports.tf").read_text()
        network = (ROOT / "tofu/opnsense/network.tf").read_text()
        variables = (ROOT / "tofu/opnsense/variables.tf").read_text()
        values = (ROOT / "tofu/opnsense/homelab.auto.tfvars").read_text()

        self.assertIn('opnsense_interfaces_vlan.managed["clients"]', imports)
        self.assertIn('47cac540-15b6-4838-9de1-f7e8e7307d2b', imports)
        self.assertIn('opnsense_kea_dhcpv4_subnet.managed["clients"]', imports)
        self.assertIn('542fde27-1972-42e1-9376-057b5cae2f5e', imports)
        self.assertNotIn("device      = each.value.device", network)
        self.assertNotIn("device      = string", variables)
        self.assertNotIn('device      = "vlan', values)
        self.assertIn("ignore_changes = [device]", network)

    def test_firewall_policy_declares_management_and_isolated_vlan_rules(self) -> None:
        values = (ROOT / "tofu/opnsense/homelab.auto.tfvars").read_text()

        for rule in (
            "management-allow-any",
            "clients-allow-dns",
            "clients-block-private",
            "infrastructure-allow-opnsense-api",
            "infrastructure-block-private",
            "guest-iot-block-private",
            "netbird-allow-private",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, values)

    def test_infrastructure_dhcp_advertises_adguard_dns(self) -> None:
        values = (ROOT / "tofu/opnsense/homelab.auto.tfvars").read_text()
        infrastructure = values.split("  infrastructure = {", 2)[2].split("  }", 1)[0]

        self.assertIn('dns_servers = ["10.0.30.10"]', infrastructure)


if __name__ == "__main__":
    unittest.main()
