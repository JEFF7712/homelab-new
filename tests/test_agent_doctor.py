import unittest
from pathlib import Path

from scripts.agent.doctor import run_doctor

ROOT = Path(__file__).resolve().parents[1]


class AgentDoctorTest(unittest.TestCase):
    def test_doctor_reports_structured_results_without_secret_values(self) -> None:
        payload = run_doctor(ROOT)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["command"], "doctor")
        self.assertTrue(payload["checks"])
        self.assertTrue(
            all(
                item["status"] in {"pass", "fail", "unavailable"}
                for item in payload["checks"]
            )
        )
        self.assertTrue(
            all(
                item["remedy"] for item in payload["checks"] if item["status"] != "pass"
            )
        )
        rendered = str(payload)
        self.assertNotIn("OPNSENSE_API_SECRET=", rendered)


if __name__ == "__main__":
    unittest.main()
