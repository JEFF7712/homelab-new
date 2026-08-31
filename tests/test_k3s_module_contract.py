from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class K3sModuleContractTests(unittest.TestCase):
    def test_k3s_server_module_declares_custom_cni_and_join_contract(self) -> None:
        module = (ROOT / "flake/modules/k3s-server.nix").read_text()

        for value in (
            'role = "server"',
            "--flannel-backend=none",
            "--disable-network-policy",
            "clusterInit",
            "serverAddress",
            "tokenFile",
            "--node-ip=${cfg.nodeIp}",
            "--advertise-address=${cfg.nodeIp}",
        ):
            with self.subTest(value=value):
                self.assertIn(value, module)

    def test_three_control_plane_profiles_reserve_static_infrastructure_ips(self) -> None:
        expected_profiles = {
            "homelab-01": "10.0.30.11",
            "homelab-02": "10.0.30.12",
            "homelab-03": "10.0.30.13",
        }

        for hostname, node_ip in expected_profiles.items():
            with self.subTest(hostname=hostname):
                profile = (ROOT / f"flake/hosts/{hostname}/default.nix").read_text()
                self.assertIn("../../modules/k3s-server.nix", profile)
                self.assertIn(f'networking.hostName = "{hostname}"', profile)
                self.assertIn(f'nodeIp = "{node_ip}"', profile)
                self.assertIn("enable = true", profile)

        primary = (ROOT / "flake/hosts/homelab-01/default.nix").read_text()
        self.assertIn("clusterInit = true", primary)

        for hostname in ("homelab-02", "homelab-03"):
            with self.subTest(hostname=hostname):
                profile = (ROOT / f"flake/hosts/{hostname}/default.nix").read_text()
                self.assertIn('serverAddress = "https://10.0.30.11:6443"', profile)
                self.assertIn('tokenFile = "/run/secrets/k3s-token"', profile)


if __name__ == "__main__":
    unittest.main()
