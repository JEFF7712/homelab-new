from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "gitops" / "voice" / "local-decision" / "app.py"


class ChoiceQ:
    def __init__(self, question: str, options: list[str]) -> None:
        self.question = question
        self.options = options


class FakeDecider:
    @classmethod
    def load(cls, model_dir: str, device: str, fast: bool) -> FakeDecider:
        return cls()

    def ask(self, state: str, questions: list[ChoiceQ], **kwargs: object) -> list[dict]:
        return [
            {"value": question.options[-1], "confidence": 0.8} for question in questions
        ]


rlcd = types.ModuleType("rlcd")
decide = types.ModuleType("rlcd.decide")
decide.ChoiceQ = ChoiceQ
decide.Decider = FakeDecider
sys.modules["rlcd"] = rlcd
sys.modules["rlcd.decide"] = decide
spec = importlib.util.spec_from_file_location("local_decision_app", APP)
assert spec is not None and spec.loader is not None
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def request() -> dict:
    return {
        "state": "turn off the kitchen lights",
        "model": "jev-1.13.0",
        "questions": {
            "action": {
                "type": "choice",
                "instructions": "Select the action.",
                "criteria": {
                    "turn_on": "Turn on",
                    "turn_off": "Turn off",
                },
            }
        },
    }


class LocalDecisionServiceTest(unittest.TestCase):
    def test_request_is_translated_and_choice_key_is_restored(self) -> None:
        state, names, questions = app.parse_request(request())
        self.assertEqual(state, "turn off the kitchen lights")
        self.assertEqual(names, ["action"])
        self.assertEqual(
            questions[0].options,
            ["turn_on: Turn on", "turn_off: Turn off"],
        )

        result = app.DecisionService("unused").decide(request())
        self.assertEqual(result["model"], app.MODEL_NAME)
        self.assertEqual(result["answers"]["action"]["choice"], "turn_off")
        self.assertEqual(result["answers"]["action"]["confidence"], 0.8)

    def test_invalid_and_oversized_requests_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            app.parse_request({"state": "x", "questions": {}})
        payload = request()
        payload["questions"]["action"]["criteria"] = {"only": "one"}
        with self.assertRaises(ValueError):
            app.parse_request(payload)
        payload = request()
        payload["state"] = "x" * (app.MAX_STATE_CHARS + 1)
        with self.assertRaises(ValueError):
            app.parse_request(payload)

    def test_metrics_contain_counts_not_transcript_or_choices(self) -> None:
        service = app.DecisionService("unused")
        service.decide(request())
        metrics = service.metrics()
        self.assertIn("jarvis_local_decision_requests_total 1", metrics)
        self.assertNotIn("kitchen", metrics)
        self.assertNotIn("turn_off", metrics)


if __name__ == "__main__":
    unittest.main()
