from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class NasDataContractTests(unittest.TestCase):
    def test_tank_pool_uses_exact_exos_disk(self) -> None:
        disk = (ROOT / "flake/hosts/nas-01/tank-config.nix").read_text()

        for value in (
            "/dev/disk/by-id/scsi-35000c500d91a3f4f",
            'pool = "tank"',
            'ashift = "12"',
            'mountpoint = "/tank/media"',
            'mountpoint = "/tank/photos"',
            'mountpoint = "/tank/documents"',
            'mountpoint = "/tank/backups"',
            'mountpoint = "/tank/cluster"',
            'mountpoint = "/tank/attic"',
            'mountpoint = "/tank/gitlab-runner"',
            'recordsize = "1M"',
        ):
            with self.subTest(value=value):
                self.assertIn(value, disk)

        self.assertNotIn("ST2000DM008", disk)
        self.assertNotIn("ZFL60NJG", disk)
        self.assertNotIn("SN520", disk)
        self.assertNotIn("/dev/sdb", disk)
        self.assertNotIn("/dev/sdc", disk)
        self.assertNotIn('mode = "mirror"', disk)

    def test_personal_datasets_use_native_encryption(self) -> None:
        disk = (ROOT / "flake/hosts/nas-01/tank-config.nix").read_text()

        self.assertEqual(disk.count('encryption = "aes-256-gcm"'), 2)
        self.assertIn("keylocation = \"file:///persist/keys/tank-photos.key\"", disk)
        self.assertIn("keylocation = \"file:///persist/keys/tank-documents.key\"", disk)

    def test_nfs_exports_only_intended_datasets(self) -> None:
        role = (ROOT / "flake/modules/nas-data.nix").read_text()
        exports = role.split("exports = ''", 1)[1].split("'';", 1)[0]

        for value in (
            "/tank/media",
            "/tank/backups",
            "/tank/cluster",
            "10.0.30.0/24(rw,sync,no_subtree_check)",
            "/tank/cluster   10.0.30.0/24(rw,sync,no_subtree_check,no_root_squash)",
            "10.0.10.0/24(ro,sync,no_subtree_check)",
        ):
            with self.subTest(value=value):
                self.assertIn(value, exports)

        self.assertNotIn("/tank/photos", exports)
        self.assertNotIn("/tank/documents", exports)
        self.assertNotIn("/tank/attic", exports)
        self.assertNotIn("/tank/gitlab-runner", exports)

    def test_snapshot_policy_matches_design_spec(self) -> None:
        role = (ROOT / "flake/modules/nas-data.nix").read_text()

        for value in (
            "services.sanoid",
            "hourly = 48;",
            "daily = 30;",
            "monthly = 12;",
            "daily = 7;",
            '"tank/photos".useTemplate = [ "personal" ]',
            '"tank/documents".useTemplate = [ "personal" ]',
            '"tank/backups".useTemplate = [ "operational" ]',
            '"tank/cluster".useTemplate = [ "operational" ]',
            '"tank/media".useTemplate = [ "weekly" ]',
            '"tank/attic".useTemplate = [ "weekly" ]',
            '"tank/gitlab-runner".useTemplate = [ "weekly" ]',
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

    def test_services_and_backup_copy_are_declared(self) -> None:
        role = (ROOT / "flake/modules/nas-data.nix").read_text()

        for value in (
            "services.atticd",
            'path = "/tank/attic"',
            "services.gitlab-runner",
            'authenticationTokenConfigFile = "/persist/gitlab-runner/authentication-token"',
            'executor = "shell"',
            'buildsDir = "/tmp/gitlab-runner-builds"',
            '"OPNsense.internal"',
            "environmentVariables",
            "makeBinPath",
            "GIT_SSL_CAINFO",
            "ata-ST2000DM008-2FR102_ZFL60NJG-part1",
            "nas-backup-2tb",
            "OnCalendar = \"daily\"",
            "/mnt/backup-2tb/photos/",
            "/mnt/backup-2tb/documents/",
            "2049",
            "8080",
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

        self.assertNotIn("ST10000NM002G", role)
        self.assertNotIn("scsi-35000c500d91a3f4f", role)


if __name__ == "__main__":
    unittest.main()
