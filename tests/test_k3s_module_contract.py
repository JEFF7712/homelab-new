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


if __name__ == "__main__":
    unittest.main()
