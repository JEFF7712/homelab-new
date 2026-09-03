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
                self.assertIn('tokenFile = "/persist/secrets/k3s-token"', profile)

    def test_primary_profile_bootstraps_pinned_cilium_before_flux(self) -> None:
        module = (ROOT / "flake/modules/k3s-server.nix").read_text()
        primary = (ROOT / "flake/hosts/homelab-01/default.nix").read_text()

        for value in (
            "bootstrapCilium",
            "services.k3s.manifests = lib.mkIf cfg.bootstrapCilium",
            'apiVersion = "helm.cattle.io/v1"',
            'version = "1.20.1"',
            "kubeProxyReplacement = true",
            'k8sServiceHost = "127.0.0.1"',
            "bgpControlPlane.enabled = true",
        ):
            with self.subTest(value=value):
                self.assertIn(value, module)

        self.assertIn("bootstrapCilium = true", primary)

    def test_module_permits_pod_traffic_to_node_plane(self) -> None:
        module = (ROOT / "flake/modules/k3s-server.nix").read_text()

        for value in (
            "--cluster-cidr=10.42.0.0/16",
            "--service-cidr=10.43.0.0/16",
            "ip saddr 10.42.0.0/16 tcp dport { 6443, 10250 } accept",
            "ip saddr 10.0.10.0/24 tcp dport 6443 accept",
            "extraReversePathFilterRules",
            "clusterPoolIPv4PodCIDRList",
            "ipv4NativeRoutingCIDR",
            "replicas = 2;",
        ):
            with self.subTest(value=value):
                self.assertIn(value, module)

    def test_nodes_carry_nfs_client_tooling(self) -> None:
        module = (ROOT / "flake/modules/k3s-server.nix").read_text()
        self.assertIn("nfs-utils", module)

    def test_module_declares_bgp_peering_and_canary(self) -> None:
        module = (ROOT / "flake/modules/k3s-server.nix").read_text()

        for value in (
            "CiliumBGPClusterConfig",
            "CiliumBGPPeerConfig",
            "CiliumBGPAdvertisement",
            "CiliumLoadBalancerIPPool",
            "localASN = 64512",
            "peerASN = 64513",
            "peerAddress = \"10.0.30.1\";",
            "10.0.40.10",
            "io.cilium/bgp-control-plane",
            "bgp-canary",
            "NET_BIND_SERVICE",
            "ingressController.enabled = true",
            "gatewayAPI.enabled = true",
        ):
            with self.subTest(value=value):
                self.assertIn(value, module)


if __name__ == "__main__":
    unittest.main()
