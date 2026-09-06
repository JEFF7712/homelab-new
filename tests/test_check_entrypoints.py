import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CheckEntrypointTest(unittest.TestCase):
    def test_required_crd_schemas_are_pinned(self) -> None:
        schema_root = ROOT / "schemas/kubernetes"
        required = {
            "clusterissuer-cert-manager-v1.json",
            "clustersecretstore-external-secrets-v1.json",
            "externalsecret-external-secrets-v1.json",
            "gatewayclass-gateway-v1.json",
            "gitrepository-source-v1.json",
            "helmrelease-helm-v2.json",
            "helmrepository-source-v1.json",
            "httproute-gateway-v1.json",
            "kustomization-kustomize-v1.json",
            "referencegrant-gateway-v1beta1.json",
            "referencegrant-gateway-v1.json",
        }
        self.assertEqual({path.name for path in schema_root.glob("*.json")}, required)

    def test_required_check_scripts_exist_and_are_executable(self) -> None:
        for name in (
            "python.sh",
            "nix.sh",
            "gitops.sh",
            "tofu.sh",
            "agent-workflows.sh",
            "all.sh",
        ):
            with self.subTest(name=name):
                path = ROOT / "scripts/checks" / name
                self.assertTrue(path.is_file())
                self.assertTrue(path.stat().st_mode & 0o111)
        for name in ("docs.py", "whitespace.py"):
            self.assertTrue((ROOT / "scripts/checks" / name).is_file())

    def test_just_exposes_offline_check_interface(self) -> None:
        result = subprocess.run(
            ["just", "--list"], cwd=ROOT, capture_output=True, text=True, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for recipe in (
            "check",
            "fmt",
            "fmt-check",
            "check-python",
            "check-nix",
            "check-gitops",
            "check-tofu",
            "check-docs",
            "provision-check-deps",
        ):
            self.assertIn(recipe, result.stdout)


if __name__ == "__main__":
    unittest.main()
