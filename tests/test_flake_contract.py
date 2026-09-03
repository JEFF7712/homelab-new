from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FlakeContractTests(unittest.TestCase):
    def test_flake_declares_required_tools(self) -> None:
        flake_path = ROOT / "flake/flake.nix"
        self.assertTrue(flake_path.is_file())
        flake = flake_path.read_text()
        for package in (
            "age",
            "sops",
            "opentofu",
            "yamllint",
            "kubeconform",
            "gitleaks",
            "glab",
            "pyright",
            "ruff",
        ):
            with self.subTest(package=package):
                self.assertIn(package, flake)

    def test_flake_exposes_formatter_and_shell(self) -> None:
        flake_path = ROOT / "flake/flake.nix"
        self.assertTrue(flake_path.is_file())
        flake = flake_path.read_text()
        self.assertIn("formatter =", flake)
        self.assertIn("devShells.default =", flake)

    def test_flake_uses_current_nixfmt_attribute(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()
        self.assertIn("formatter = pkgs.nixfmt;", flake)

    def test_flake_check_runs_repository_tests(self) -> None:
        flake = (ROOT / "flake/flake.nix").read_text()
        self.assertIn("python -m unittest discover -s tests", flake)


if __name__ == "__main__":
    unittest.main()
