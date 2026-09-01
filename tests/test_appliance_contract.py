import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "flake/hosts/adguard-netbird-01"


class ApplianceContractTests(unittest.TestCase):
    def test_flake_exports_installable_appliance(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()

        self.assertIn("disko.nixosModules.disko", flake)
        self.assertIn("impermanence.nixosModules.impermanence", flake)
        self.assertIn("nixosConfigurations.adguard-netbird-01", flake)

    def test_storage_targets_only_internal_sata_disk(self) -> None:
        storage = (HOST / "disk-config.nix").read_text()

        self.assertIn('device = "/dev/sda"', storage)
        self.assertNotIn('device = "/dev/sdb"', storage)
        self.assertIn('type = "luks"', storage)
        self.assertIn('passwordFile = "/tmp/adguard-netbird-01-luks.key"', storage)
        self.assertIn('"tpm2-device=auto"', storage)
        for mountpoint in ('mountpoint = "/nix"', 'mountpoint = "/persist"', 'mountpoint = "/var/log"'):
            with self.subTest(mountpoint=mountpoint):
                self.assertIn(mountpoint, storage)

    def test_host_uses_tmpfs_root_and_observed_hardware(self) -> None:
        host = (HOST / "default.nix").read_text()
        hardware = (HOST / "hardware-configuration.nix").read_text()

        self.assertIn('fsType = "tmpfs"', host)
        self.assertIn('device = "none"', host)
        self.assertIn('fileSystems."/persist".neededForBoot = true', host)
        self.assertIn('"ahci"', hardware)
        self.assertIn('"sd_mod"', hardware)
        self.assertIn('"r8169"', hardware)
        self.assertIn('hostPlatform = lib.mkDefault "x86_64-linux"', hardware)

    def test_networking_declares_infrastructure_and_netbird_segments(self) -> None:
        role = (ROOT / "flake/modules/adguard-netbird-appliance.nix").read_text()

        self.assertIn('Address = "10.0.30.10/24"', role)
        self.assertIn('Gateway = "10.0.30.1"', role)
        self.assertIn('Id = 60', role)
        self.assertIn('Address = "10.0.60.2/24"', role)
        self.assertIn('nftables.enable = true', role)
        self.assertIn(
            'iifname "wt0" tcp dport { 22, 53, 3000 } accept', role
        )
        self.assertIn('iifname "wt0" udp dport 53 accept', role)

    def test_services_and_persistence_are_declarative(self) -> None:
        role = (ROOT / "flake/modules/adguard-netbird-appliance.nix").read_text()

        self.assertIn("services.adguardhome", role)
        self.assertIn('host = "10.0.30.10"', role)
        self.assertIn('"https://dns.quad9.net/dns-query"', role)
        self.assertIn('useRoutingFeatures = "server"', role)
        self.assertIn('mutableSettings = false', role)
        self.assertIn('PasswordAuthentication = false', role)
        self.assertIn('openFirewall = false', role)
        self.assertNotIn('      "/etc/ssh"\n', role)
        self.assertIn('path = "/persist/etc/ssh/ssh_host_ed25519_key"', role)
        self.assertIn('path = "/persist/etc/ssh/ssh_host_rsa_key"', role)
        self.assertIn('after = [ "network-online.target" ]', role)
        self.assertIn('wants = [ "network-online.target" ]', role)
        self.assertIn('serviceConfig.StateDirectoryMode = "0700"', role)
        self.assertIn('d /var/lib/private 0700 root root -', role)
        self.assertIn(
            'd /persist/var/lib/private/AdGuardHome 0700 nobody nogroup -', role
        )
        for path in (
            '"/var/lib/private/AdGuardHome"',
            '"/var/lib/netbird"',
            '"/var/lib/nixos"',
            '"/var/lib/systemd"',
        ):
            with self.subTest(path=path):
                self.assertIn(path, role)


if __name__ == "__main__":
    unittest.main()
