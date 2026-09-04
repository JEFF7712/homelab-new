import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from opnsense_reconciler.check_plan import baked_uri, check_plan_file, main


def plan_doc(uri: str) -> dict:
    return {"variables": {"opnsense_uri": {"value": uri}}}


class CheckPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_plan(self, doc: dict) -> Path:
        path = Path(self.tmp.name) / "plan.json"
        path.write_text(json.dumps(doc))
        return path

    def test_matching_uri_returns_it(self) -> None:
        path = self.write_plan(plan_doc("https://OPNsense.internal"))
        self.assertEqual(
            check_plan_file(path, "https://OPNsense.internal"),
            "https://OPNsense.internal",
        )

    def test_mismatched_uri_raises(self) -> None:
        path = self.write_plan(plan_doc("https://192.168.1.1"))
        with self.assertRaisesRegex(ValueError, "expected"):
            check_plan_file(path, "https://OPNsense.internal")

    def test_missing_variables_raises(self) -> None:
        with self.assertRaises(ValueError):
            baked_uri({})

    def test_missing_uri_entry_raises(self) -> None:
        with self.assertRaises(ValueError):
            baked_uri({"variables": {}})

    def test_main_prints_checked_uri(self) -> None:
        path = self.write_plan(plan_doc("https://OPNsense.internal"))
        out = io.StringIO()
        with redirect_stdout(out):
            main(["--plan", str(path), "--expect-uri", "https://OPNsense.internal"])
        self.assertEqual(
            json.loads(out.getvalue()), {"opnsense_uri": "https://OPNsense.internal"}
        )


if __name__ == "__main__":
    unittest.main()
