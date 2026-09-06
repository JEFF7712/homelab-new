import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class NasContractTests(unittest.TestCase):
    def test_flake_exports_installable_nas(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()

        self.assertIn("nixosConfigurations.nas-01", flake)
        self.assertIn("./hosts/nas-01", flake)
        self.assertIn("disko.nixosModules.disko", flake)
        self.assertIn("impermanence.nixosModules.impermanence", flake)

    def test_system_pool_uses_exact_encrypted_mirrored_nvmes(self) -> None:
        disk = (ROOT / "flake/hosts/nas-01/disk-config.nix").read_text()

        for value in (
            "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022C1800396",
            "/dev/disk/by-id/nvme-WDC_PC_SN520_SDAPNUW-256G-1006_2022BA804857",
            'name = "nas-system-a"',
            'name = "nas-system-b"',
            'passwordFile = "/tmp/nas-01-system.key"',
            'pool = "zroot"',
            'mode = "mirror"',
            'mountpoint = "/boot"',
            'mountpoint = "/boot-fallback"',
            'mountpoint = "/nix"',
            'mountpoint = "/persist"',
            'mountpoint = "/var/log"',
        ):
            with self.subTest(value=value):
                self.assertIn(value, disk)

        self.assertNotIn("ST2000DM008", disk)
        self.assertNotIn("ST10000NM002G", disk)
        self.assertNotIn("/dev/sdb", disk)
        self.assertNotIn("/dev/sdc", disk)

    def test_host_declares_observed_hardware_and_static_network(self) -> None:
        hardware = (ROOT / "flake/hosts/nas-01/hardware-configuration.nix").read_text()
        role = (ROOT / "flake/modules/nas-base.nix").read_text()

        for module in ("mpt3sas", "nvme", "r8169", "kvm-amd"):
            with self.subTest(module=module):
                self.assertIn(module, hardware)

        for value in (
            'Address = "10.0.30.20/24"',
            'DNS = "10.0.30.10"',
            'Gateway = "10.0.30.1"',
            'matchConfig.Name = "enp5s0"',
            'networking.hostId = "31eabe12"',
            "services.smartd",
            "services.zfs.autoScrub",
            "services.zfs.trim",
            "ip saddr 10.0.30.0/24 tcp dport 22 accept",
            'devices = [ "nodev" ]',
            'path = "/boot"',
            'path = "/boot-fallback"',
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

    def test_host_uses_ephemeral_root_and_persists_identity(self) -> None:
        host = (ROOT / "flake/hosts/nas-01/default.nix").read_text()
        role = (ROOT / "flake/modules/nas-base.nix").read_text()

        self.assertIn('fsType = "tmpfs"', host)
        self.assertIn('fileSystems."/persist".neededForBoot = true', host)
        self.assertIn('environment.persistence."/persist"', role)
        self.assertIn('files = [ "/etc/machine-id" ]', role)
        self.assertIn("PasswordAuthentication = false", role)
        self.assertIn('PermitRootLogin = "no"', role)


if __name__ == "__main__":
    unittest.main()
