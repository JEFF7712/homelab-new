from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "flake/hosts/homelab-02"


class K3sNodeInstallationContractTests(unittest.TestCase):
    def test_flake_exports_installable_homelab_02(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()

        self.assertIn("nixosConfigurations.homelab-02", flake)
        self.assertIn("./hosts/homelab-02", flake)
        self.assertIn("disko.nixosModules.disko", flake)
        self.assertIn("impermanence.nixosModules.impermanence", flake)

    def test_storage_targets_only_observed_internal_ssd(self) -> None:
        storage = (HOST / "disk-config.nix").read_text()

        self.assertIn(
            "/dev/disk/by-id/ata-FORESEE_64GB_SSD_0000007520__FMA39721",
            storage,
        )
        self.assertNotIn('/dev/sdb', storage)
        self.assertNotIn('type = "luks"', storage)
        self.assertIn('mountpoint = "/boot"', storage)
        for mountpoint in ("/nix", "/persist", "/var/log"):
            with self.subTest(mountpoint=mountpoint):
                self.assertIn(f'mountpoint = "{mountpoint}"', storage)

    def test_host_declares_observed_hardware_and_ephemeral_root(self) -> None:
        host = (HOST / "default.nix").read_text()
        hardware = (HOST / "hardware-configuration.nix").read_text()

        for module in ("xhci_pci", "ahci", "sd_mod", "r8169", "kvm-amd"):
            with self.subTest(module=module):
                self.assertIn(module, hardware)
        self.assertIn('fsType = "tmpfs"', host)
        self.assertIn('fileSystems."/persist".neededForBoot = true', host)
        self.assertIn('primaryInterface = "enp1s0"', host)
        self.assertIn('nodeIp = "10.0.30.12"', host)
        self.assertIn('tokenFile = "/persist/secrets/k3s-token"', host)

    def test_role_provides_uefi_network_security_and_persistence(self) -> None:
        role = (ROOT / "flake/modules/k3s-server.nix").read_text()

        for value in (
            "systemd-boot.enable = true",
            'Address = "${cfg.nodeIp}/24"',
            'DNS = "10.0.30.10"',
            'Gateway = "10.0.30.1"',
            "cfg.primaryInterface",
            "PasswordAuthentication = false",
            'PermitRootLogin = "no"',
            'environment.persistence."/persist"',
            '"/var/lib/rancher/k3s"',
            'files = [ "/etc/machine-id" ]',
            "ConditionPathExists",
            "services.smartd",
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

    def test_joining_node_omits_the_entire_cilium_manifest(self) -> None:
        role = (ROOT / "flake/modules/k3s-server.nix").read_text()

        self.assertIn(
            "services.k3s.manifests = lib.mkIf cfg.bootstrapCilium", role
        )
        self.assertNotIn(
            "services.k3s.manifests.cilium.content = lib.mkIf", role
        )


if __name__ == "__main__":
    unittest.main()
