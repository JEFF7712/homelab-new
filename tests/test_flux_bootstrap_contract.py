from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FluxBootstrapContractTests(unittest.TestCase):
    def test_flux_system_bootstrap_files_exist(self) -> None:
        for relative_path in (
            "gitops/clusters/homelab-01/flux-system/gotk-components.yaml",
            "gitops/clusters/homelab-01/flux-system/gotk-sync.yaml",
            "gitops/clusters/homelab-01/flux-system/kustomization.yaml",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_platform_layer_declares_pinned_eso(self) -> None:
        release = (ROOT / "gitops/platform/external-secrets/release.yaml").read_text()
        self.assertIn("kind: HelmRelease", release)
        self.assertIn("chart: external-secrets", release)
        self.assertIn("version: ", release)

    def test_layers_chain_with_depends_on(self) -> None:
        eso = (ROOT / "gitops/clusters/homelab-01/eso.yaml").read_text()
        self.assertIn("dependsOn", eso)
        self.assertIn("name: secrets", eso)

    def test_sops_policy_names_single_age_recipient(self) -> None:
        policy = (ROOT / ".sops.yaml").read_text()
        self.assertIn("age:", policy)
        self.assertNotIn("TODO", policy)

    def test_no_plaintext_tokens_in_gitops(self) -> None:
        for path in (ROOT / "gitops").rglob("*.yaml"):
            with self.subTest(path=str(path)):
                self.assertNotRegex(path.read_text(), r"glpat-[A-Za-z0-9_-]{20,}")

    def test_storage_layer_declares_nfs_provisioner(self) -> None:
        release = (ROOT / "gitops/storage/nfs/release.yaml").read_text()
        for value in (
            "chart: nfs-subdir-external-provisioner",
            "version: ",
            "10.0.30.20",
            "/tank/cluster",
            "nfs-cluster",
        ):
            with self.subTest(value=value):
                self.assertIn(value, release)

        layer = (ROOT / "gitops/clusters/homelab-01/storage.yaml").read_text()
        self.assertIn("name: platform", layer)


if __name__ == "__main__":
    unittest.main()
