"""Fixture-scored bench for Jev decision-model candidates.

Reads recorded model outputs from tests/fixtures/jev_decisions/<model>.json
(produced by scripts/record_jev_decisions.py), replays each payload through
router.decide, and scores route accuracy, field accuracy, false-action rate,
calibration (ECE), and latency.

Model quality never fails this test: it is a measurement instrument, not a
gate. Harness problems (missing fixtures, unknown case ids, malformed
payloads) fail loudly. Unit tests below cover the scoring math with inline
payloads so the scorer itself is verified without any model.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "home-assistant" / "custom_components" / "jarvis_jev"
CORPUS_PATH = ROOT / "tests" / "jev_decision_corpus.yaml"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "jev_decisions"

GATED_QUESTIONS = ("request_kind", "target", "action", "reference")


def load_router():
    package = types.ModuleType("jarvis_jev")
    package.__path__ = [str(PACKAGE_DIR)]
    sys.modules["jarvis_jev"] = package
    for name in ("const", "router"):
        spec = importlib.util.spec_from_file_location(
            f"jarvis_jev.{name}", PACKAGE_DIR / f"{name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"jarvis_jev.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules["jarvis_jev.router"]


router = load_router()


def normalize_payload(payload: dict) -> dict:
    """Copy a recorded payload so router.decide accepts it.

    decide() rejects payloads whose model id differs from the pinned Jev
    model. Bench scoring must run the identical decide() path for every
    candidate, so the recorded id is preserved under _recorded_model and
    the live id is set for scoring.
    """
    normalized = json.loads(json.dumps(payload))
    normalized["_recorded_model"] = normalized.get("model")
    normalized["model"] = router.MODEL if hasattr(router, "MODEL") else "jev-1.13.0"
    return normalized


def min_confidence(payload: dict) -> float | None:
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return None
    confidences = []
    for name in GATED_QUESTIONS:
        answer = answers.get(name)
        if not isinstance(answer, dict):
            return None
        confidence = answer.get("confidence")
        if not isinstance(confidence, (int, float)):
            return None
        confidences.append(float(confidence))
    if payload.get("answers", {}).get("action", {}).get("choice") == "set_color":
        color = payload["answers"].get("color", {})
        if not isinstance(color.get("confidence"), (int, float)):
            return None
        confidences.append(float(color["confidence"]))
    return min(confidences)


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(pct / 100 * len(ordered)))
    return ordered[index]


def expected_calibration_error(
    confidences: list[float], correct: list[bool], bins: int = 10
) -> float | None:
    if not confidences or len(confidences) != len(correct):
        return None
    totals = [0] * bins
    hits = [0] * bins
    conf_sums = [0.0] * bins
    for confidence, hit in zip(confidences, correct):
        index = min(bins - 1, int(confidence * bins))
        totals[index] += 1
        hits[index] += hit
        conf_sums[index] += confidence
    total = len(confidences)
    ece = 0.0
    for i in range(bins):
        if totals[i]:
            ece += (
                abs(hits[i] / totals[i] - conf_sums[i] / totals[i]) * totals[i] / total
            )
    return ece


def score_case(case: dict, payload: dict) -> dict:
    """Score one recorded payload. Never raises on model content."""
    say = case["say"]
    expected_route = case["expected_route"]
    decision = router.decide(say, normalize_payload(payload))
    outcome: dict = {
        "id": case["id"],
        "expected_route": expected_route,
        "route": decision.route,
        "route_ok": decision.route == expected_route,
        "false_action": False,
        "field_ok": None,
        "confidence": min_confidence(payload),
    }
    if expected_route == "execute":
        command = decision.command
        expected = case["expected"]
        if command is None:
            outcome["false_action"] = decision.route == "execute"
            outcome["field_ok"] = False
        else:
            match = (
                command.target == expected["target"]
                and command.action == expected["action"]
                and command.color == expected.get("color", "none_or_unknown")
                and (command.value == case.get("value"))
            )
            outcome["field_ok"] = match
            outcome["false_action"] = not match
    else:
        outcome["false_action"] = decision.route == "execute"
    return outcome


def summarize(outcomes: list[dict], latencies: list[float]) -> dict:
    total = len(outcomes)
    route_ok = sum(1 for o in outcomes if o["route_ok"])
    false_actions = sum(1 for o in outcomes if o["false_action"])
    executed = [o for o in outcomes if o["expected_route"] == "execute"]
    exec_fields = [o for o in executed if o["field_ok"]]
    confidences = [o["confidence"] for o in outcomes if o["confidence"] is not None]
    correctness = [o["route_ok"] for o in outcomes if o["confidence"] is not None]
    by_category: dict[str, dict] = {}
    for outcome in outcomes:
        category = outcome["id"].split("-")[0]
        bucket = by_category.setdefault(
            category, {"total": 0, "route_ok": 0, "false_action": 0}
        )
        bucket["total"] += 1
        bucket["route_ok"] += outcome["route_ok"]
        bucket["false_action"] += outcome["false_action"]
    return {
        "total": total,
        "route_acc": route_ok / total if total else None,
        "false_actions": false_actions,
        "false_action_rate": false_actions / total if total else None,
        "execute_field_acc": len(exec_fields) / len(executed) if executed else None,
        "ece": expected_calibration_error(confidences, correctness),
        "latency_p50_ms": percentile(latencies, 50),
        "latency_p95_ms": percentile(latencies, 95),
        "by_category": by_category,
    }


def load_fixtures() -> dict[str, dict]:
    if not FIXTURE_DIR.is_dir():
        return {}
    fixtures = {}
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            fixtures[path.stem] = json.load(f)
    return fixtures


def choice(value: str, confidence: float = 0.99) -> dict:
    return {"type": "choice", "choice": value, "confidence": confidence}


def payload_for(
    kind: str = "home_command",
    target: str = "kitchen_lights",
    action: str = "turn_off",
    reference: str = "explicit_target",
    color: str = "none_or_unknown",
    confidence: float = 0.99,
) -> dict:
    return {
        "model": "candidate",
        "answers": {
            "request_kind": choice(kind, confidence),
            "target": choice(target, confidence),
            "action": choice(action, confidence),
            "reference": choice(reference, confidence),
            "color": choice(color, confidence),
        },
    }


class BenchScoringTest(unittest.TestCase):
    def test_normalize_preserves_recorded_model(self) -> None:
        normalized = normalize_payload(payload_for())
        self.assertEqual(normalized["_recorded_model"], "candidate")
        decision = router.decide(
            "Turn off the kitchen lights.", normalize_payload(payload_for())
        )
        self.assertEqual(decision.route, "execute")

    def test_wrong_target_is_false_action(self) -> None:
        case = {
            "id": "x",
            "say": "Turn off the kitchen lights.",
            "expected_route": "execute",
            "expected": {
                "target": "kitchen_lights",
                "action": "turn_off",
                "color": "none_or_unknown",
            },
        }
        outcome = score_case(case, payload_for(target="living_room_lights"))
        self.assertTrue(outcome["route_ok"])
        self.assertFalse(outcome["field_ok"])
        self.assertTrue(outcome["false_action"])

    def test_correct_noncolor_execute_matches_absent_color(self) -> None:
        case = {
            "id": "x",
            "say": "Turn off the kitchen lights.",
            "expected_route": "execute",
            "expected": {
                "target": "kitchen_lights",
                "action": "turn_off",
                "color": "none_or_unknown",
            },
        }
        outcome = score_case(case, payload_for())
        self.assertTrue(outcome["route_ok"])
        self.assertTrue(outcome["field_ok"])
        self.assertFalse(outcome["false_action"])

    def test_unexpected_execute_is_false_action(self) -> None:
        case = {
            "id": "y",
            "say": "Turn that back on.",
            "expected_route": "clarify",
            "expected": {"request_kind": "home_command"},
        }
        outcome = score_case(
            case,
            payload_for(
                target="kitchen_lights", action="turn_on", reference="explicit_target"
            ),
        )
        self.assertFalse(outcome["route_ok"])
        self.assertTrue(outcome["false_action"])

    def test_correct_clarify_is_not_false_action(self) -> None:
        case = {
            "id": "z",
            "say": "Turn that back on.",
            "expected_route": "clarify",
            "expected": {"request_kind": "home_command"},
        }
        outcome = score_case(
            case,
            payload_for(
                target="none_or_unknown",
                action="none_or_unsupported",
                reference="missing_or_ambiguous",
            ),
        )
        self.assertTrue(outcome["route_ok"])
        self.assertFalse(outcome["false_action"])

    def test_ece_zero_for_perfectly_calibrated(self) -> None:
        ece = expected_calibration_error(
            [1.0, 1.0, 0.0, 0.0], [True, True, False, False]
        )
        self.assertAlmostEqual(ece or 0.0, 0.0, places=6)

    def test_percentile_edges(self) -> None:
        self.assertIsNone(percentile([], 50))
        self.assertEqual(percentile([3.0, 1.0, 2.0], 50), 2.0)


class FixtureBenchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(CORPUS_PATH, encoding="utf-8") as f:
            cls.cases = {c["id"]: c for c in yaml.safe_load(f)}
        cls.fixtures = load_fixtures()
        if not cls.fixtures:
            raise unittest.SkipTest(
                "no recorded fixtures in tests/fixtures/jev_decisions/; "
                "run scripts/record_jev_decisions.py against a candidate first"
            )

    def test_fixture_models(self) -> None:
        for label, fixture in self.fixtures.items():
            with self.subTest(model=label):
                results = fixture.get("results")
                self.assertIsInstance(results, dict, f"{label}: no results map")
                unknown = sorted(set(results) - set(self.cases))
                self.assertEqual(unknown, [], f"{label}: unknown case ids {unknown}")
                latencies = []
                outcomes = []
                for case_id, record in results.items():
                    self.assertIn("payload", record, f"{label}/{case_id}")
                    payload = record["payload"]
                    self.assertIsInstance(
                        payload.get("answers"), dict, f"{label}/{case_id}"
                    )
                    if isinstance(record.get("latency_ms"), (int, float)):
                        latencies.append(float(record["latency_ms"]))
                    outcomes.append(score_case(self.cases[case_id], payload))
                summary = summarize(outcomes, latencies)
                print(f"\n[{label}] {json.dumps(summary, indent=2, sort_keys=True)}")
                self.assertEqual(
                    summary["total"],
                    len(self.cases),
                    f"{label}: fixture covers {summary['total']}/{len(self.cases)} cases",
                )


if __name__ == "__main__":
    unittest.main()
