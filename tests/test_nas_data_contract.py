import unittest
from pathlib import Path

import yaml

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
        self.assertIn('keylocation = "file:///persist/keys/tank-photos.key"', disk)
        self.assertIn('keylocation = "file:///persist/keys/tank-documents.key"', disk)

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
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

    def test_services_and_backup_copy_are_declared(self) -> None:
        role = (ROOT / "flake/modules/nas-data.nix").read_text()

        for value in (
            "services.atticd",
            'path = "/tank/attic"',
            "services.gitlab-runner",
            "settings.concurrent = 2;",
            'authenticationTokenConfigFile = "/persist/gitlab-runner/authentication-token"',
            'authenticationTokenConfigFile = "/persist/gitlab-runner/ci-authentication-token"',
            'executor = "shell"',
            'buildsDir = "/tmp/gitlab-runner-builds"',
            'buildsDir = "/tmp/gitlab-runner-ci-builds"',
            "services.nas-ci",
            "limit = 1;",
            "requestConcurrency = 1;",
            '"OPNsense.internal"',
            "DynamicUser = lib.mkForce false",
            'User = "gitlab-runner"',
            '"network-online.target"',
            'Restart = "on-failure"',
            "environmentVariables",
            "makeBinPath",
            "GIT_SSL_CAINFO",
            "ata-ST2000DM008-2FR102_ZFL60NJG-part1",
            "nas-backup-2tb",
            'OnCalendar = "daily"',
            "/mnt/backup-2tb/photos/",
            "/mnt/backup-2tb/documents/",
            "2049",
            "8080",
        ):
            with self.subTest(value=value):
                self.assertIn(value, role)

        self.assertNotIn("ST10000NM002G", role)
        self.assertNotIn("scsi-35000c500d91a3f4f", role)

    def test_ci_runner_lanes_preserve_the_credential_boundary(self) -> None:
        pipeline = yaml.safe_load((ROOT / ".gitlab-ci.yml").read_text())

        self.assertEqual(pipeline[".nas_ci"]["tags"], ["nas-ci"])

        for name in (
            "nix_format",
            "repository_tests",
            "yaml_schema",
            "secret_scan",
        ):
            with self.subTest(job=name):
                self.assertIn(".nas_ci", pipeline[name]["extends"])

        for name in (
            "nix_format_feature",
            "repository_tests_feature",
            "yaml_schema_feature",
            "secret_scan_feature",
        ):
            with self.subTest(job=name):
                self.assertIn(".shared_feature", pipeline[name]["extends"])

        for name in (
            "opnsense_inventory",
            "opnsense_plan",
            "opnsense_apply",
            "deploy_host",
        ):
            with self.subTest(job=name):
                self.assertEqual(pipeline[name]["tags"], ["nas-privileged"])
                self.assertEqual(pipeline[name]["environment"], {"name": "production"})


if __name__ == "__main__":
    unittest.main()
