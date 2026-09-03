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
            "clients-allow-load-balancers",
            "clients-block-private",
            "clients-allow-internet",
            "infrastructure-allow-dns",
            "infrastructure-allow-opnsense-api",
            "infrastructure-allow-load-balancers",
            "infrastructure-allow-bgp",
            "infrastructure-block-private",
            "infrastructure-allow-internet",
            "load-balancers-allow-any",
            "guest-iot-allow-dns",
            "guest-iot-block-private",
            "guest-iot-allow-internet",
            "netbird-allow-private",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, values)

    def test_firewall_filters_are_imported_by_live_uuid(self) -> None:
        imports = (ROOT / "tofu/opnsense/imports.tf").read_text()

        expected = {
            'opnsense_firewall_filter.managed["management-allow-any"]': "95858af2-62f3-4a36-99b8-7319f3d66492",
            'opnsense_firewall_filter.managed["clients-allow-dns"]': "f502906a-0682-48b7-8f1a-0200d8f9b9cb",
            'opnsense_firewall_filter.managed["clients-allow-load-balancers"]': "4b5b96ac-4904-4b51-ad4b-82571ef4d7c0",
            'opnsense_firewall_filter.managed["clients-block-private"]': "d9d493ab-2b2f-456e-9e95-b127049c3a5f",
            'opnsense_firewall_filter.managed["clients-allow-internet"]': "53dbf3e1-5061-466b-b67e-28b6320120ca",
            'opnsense_firewall_filter.managed["infrastructure-allow-dns"]': "58f85612-4eec-4cba-af07-44e8b6606408",
            'opnsense_firewall_filter.managed["infrastructure-allow-opnsense-api"]': "a3f8e957-48da-4f3c-b68b-553c367d1f54",
            'opnsense_firewall_filter.managed["infrastructure-allow-load-balancers"]': "f790dc6d-d612-497d-ac1c-14cd3b0fdd2c",
            'opnsense_firewall_filter.managed["infrastructure-allow-bgp"]': "b14e08e0-16a9-4ba3-a847-c1ee5d0565b7",
            'opnsense_firewall_filter.managed["infrastructure-block-private"]': "162e80ff-5866-417e-aa2c-ef9437d3ae28",
            'opnsense_firewall_filter.managed["infrastructure-allow-internet"]': "309a589a-0e10-4380-8950-89682c65cf9f",
            'opnsense_firewall_filter.managed["load-balancers-allow-any"]': "93f7252f-d586-4d32-b92e-3a358e9e34dc",
            'opnsense_firewall_filter.managed["guest-iot-allow-dns"]': "ba8de459-7e17-4639-b280-b58bd8910351",
            'opnsense_firewall_filter.managed["guest-iot-block-private"]': "5507adaa-d137-42ed-82d5-75959df55ca7",
            'opnsense_firewall_filter.managed["guest-iot-allow-internet"]': "f0c82562-9a39-4530-9c4e-4247bcb641cf",
            'opnsense_firewall_filter.managed["netbird-allow-private"]': "58fe1b1a-e896-45f5-a2e0-93d59eb14d6e",
        }

        for address, uuid in expected.items():
            with self.subTest(address=address):
                self.assertIn(address, imports)
                self.assertIn(uuid, imports)

        for out_of_scope in (
            "e3900737ad5e1652033d67c58521ef51",
            "02f4bab031b57d1e30553ce08e0ec131",
        ):
            with self.subTest(out_of_scope=out_of_scope):
                self.assertNotIn(out_of_scope, imports)

    def test_infrastructure_bgp_rule_declares_tcp_179(self) -> None:
        values = (ROOT / "tofu/opnsense/homelab.auto.tfvars").read_text()
        bgp = values.split("infrastructure-allow-bgp = {", 1)[1].split("\n  }\n", 1)[0]

        self.assertIn("sequence    = 315", bgp)
        self.assertIn('interface   = { interface = ["opt3"] }', bgp)
        self.assertIn('destination = { net = "10.0.30.1", port = "179" }', bgp)
        self.assertIn('source      = { net = "10.0.30.0/24", port = "" }', bgp)

    def test_all_vlan_and_subnet_state_is_imported(self) -> None:
        imports = (ROOT / "tofu/opnsense/imports.tf").read_text()

        expected = {
            'opnsense_interfaces_vlan.managed["management"]': "b21e1b33-6cc0-4cf1-a8d0-71a71bbb5cbf",
            'opnsense_interfaces_vlan.managed["clients"]': "47cac540-15b6-4838-9de1-f7e8e7307d2b",
            'opnsense_interfaces_vlan.managed["infrastructure"]': "32023e94-4ed8-4494-a3ac-9256107b513b",
            'opnsense_interfaces_vlan.managed["load-balancers"]': "596bc09b-5830-47be-8007-da0b72044e5a",
            'opnsense_interfaces_vlan.managed["guest-iot"]': "ce795785-9b56-463e-b621-9abf121684b6",
            'opnsense_interfaces_vlan.managed["netbird"]': "d118a662-22cf-4134-8047-7e334c5f5c6e",
            'opnsense_kea_dhcpv4_subnet.managed["management"]': "b0644f73-95b1-478b-8485-4fbfaa293116",
            'opnsense_kea_dhcpv4_subnet.managed["clients"]': "542fde27-1972-42e1-9376-057b5cae2f5e",
            'opnsense_kea_dhcpv4_subnet.managed["infrastructure"]': "c0848ac2-1f08-4326-bd04-2d36d61ba722",
            'opnsense_kea_dhcpv4_subnet.managed["guest-iot"]': "ed37170d-230a-4d70-81af-8a5b06077962",
        }

        for address, uuid in expected.items():
            with self.subTest(address=address):
                self.assertIn(address, imports)
                self.assertIn(uuid, imports)

        self.assertNotIn("15e22a34-8bb2-4bf8-b26e-b1db576655c5", imports)

    def test_infrastructure_dhcp_advertises_adguard_dns(self) -> None:
        values = (ROOT / "tofu/opnsense/homelab.auto.tfvars").read_text()
        infrastructure = values.split("  infrastructure = {", 2)[2].split("  }", 1)[0]

        self.assertIn('dns_servers = ["10.0.30.10"]', infrastructure)


if __name__ == "__main__":
    unittest.main()
