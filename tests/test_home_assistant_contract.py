import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME_ASSISTANT = ROOT / "gitops/home-assistant"


class HomeAssistantContractTests(unittest.TestCase):
    def test_flux_layer_owns_home_assistant(self) -> None:
        layer = (ROOT / "gitops/clusters/homelab-01/home-assistant.yaml").read_text()

        self.assertIn("path: ./gitops/home-assistant", layer)
        self.assertIn("name: eso", layer)
        self.assertIn("name: storage", layer)

    def test_stateful_workloads_have_safe_storage_boundaries(self) -> None:
        volumes = list(
            yaml.safe_load_all((HOME_ASSISTANT / "volumes.yaml").read_text())
        )
        claims = {volume["metadata"]["name"]: volume for volume in volumes}

        self.assertEqual(
            claims["home-assistant-config"]["spec"]["storageClassName"], "nfs-cluster"
        )
        self.assertEqual(
            claims["home-assistant-postgres-data"]["spec"]["storageClassName"],
            "nvme-homelab-01",
        )

    def test_single_instance_home_assistant_uses_postgres_and_secret_file(self) -> None:
        deployment = yaml.safe_load((HOME_ASSISTANT / "deployment.yaml").read_text())
        config = yaml.safe_load((HOME_ASSISTANT / "config.yaml").read_text())
        external_secret = yaml.safe_load((HOME_ASSISTANT / "secrets.yaml").read_text())

        self.assertEqual(deployment["spec"]["replicas"], 1)
        self.assertEqual(deployment["spec"]["strategy"]["type"], "Recreate")
        self.assertNotIn("hostNetwork", deployment["spec"]["template"]["spec"])
        self.assertIn("!secret recorder_db_url", config["data"]["configuration.yaml"])
        secrets = yaml.safe_load(
            external_secret["spec"]["target"]["template"]["data"]["secrets.yaml"]
        )
        self.assertEqual(
            secrets["recorder_db_url"],
            "postgresql://homeassistant:{{ .db_password }}@"
            "home-assistant-postgres.home-assistant.svc.cluster.local:5432/homeassistant",
        )

    def test_postgres_backup_follows_home_assistant_reconciliation(self) -> None:
        backup_layer = (ROOT / "gitops/clusters/homelab-01/backups.yaml").read_text()
        dump = (ROOT / "gitops/backups/home-assistant-db-dump.yaml").read_text()

        self.assertIn("name: home-assistant", backup_layer)
        self.assertIn("home-assistant-postgres.home-assistant", dump)
        self.assertIn("home-assistant-db-password", dump)


if __name__ == "__main__":
    unittest.main()
