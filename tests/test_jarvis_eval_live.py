"""Offline tests for the live eval's pure evaluation logic.

No Home Assistant connection; all runs use canned intent-stage events.
"""

from __future__ import annotations

import unittest

from scripts.jarvis_eval import evaluate


def intent_end_event(
    processed: bool,
    speech: str = "Done.",
    success: list | None = None,
    failed: list | None = None,
) -> list:
    return [
        {"type": "run-start", "data": {}},
        {
            "type": "intent-end",
            "data": {
                "processed_locally": processed,
                "intent_output": {
                    "response": {
                        "speech": {"plain": {"speech": speech}},
                        "data": {
                            "success": (
                                [{"id": "light.kitchen_lights"}]
                                if success is None
                                else success
                            ),
                            "failed": [] if failed is None else failed,
                        },
                    }
                },
            },
        },
        {"type": "run-end", "data": None},
    ]


LOCAL_CASE = {
    "id": "lights-kitchen-on",
    "say": "Turn on the kitchen lights.",
    "path": "local",
    "intent": "HassTurnOn",
    "targets": ["light.kitchen_lights"],
    "response": "Done.",
}

LLM_CASE = {
    "id": "general-question",
    "say": "How many ounces are in a cup?",
    "path": "llm",
    "tool": "none",
}


class EvaluateTest(unittest.TestCase):
    def test_local_routing_pass(self) -> None:
        res = evaluate(LOCAL_CASE, intent_end_event(True))
        self.assertTrue(res["ok"])
        self.assertEqual(res["failures"], [])

    def test_local_misroute_fails(self) -> None:
        res = evaluate(LOCAL_CASE, intent_end_event(False, speech=""))
        self.assertFalse(res["ok"])
        self.assertTrue(any("processed_locally" in f for f in res["failures"]))

    def test_local_reply_mismatch_fails(self) -> None:
        res = evaluate(LOCAL_CASE, intent_end_event(True, speech="Okay."))
        self.assertFalse(res["ok"])
        self.assertTrue(any("reply mismatch" in f for f in res["failures"]))

    def test_local_action_outside_targets_fails(self) -> None:
        res = evaluate(
            LOCAL_CASE,
            intent_end_event(True, success=[{"id": "light.garage_disco"}]),
        )
        self.assertFalse(res["ok"])
        self.assertTrue(any("outside targets" in f for f in res["failures"]))

    def test_local_failed_targets_fail(self) -> None:
        res = evaluate(
            LOCAL_CASE,
            intent_end_event(
                True,
                success=[{"id": "light.kitchen_lights"}],
                failed=[{"id": "light.kitchen_lights"}],
            ),
        )
        self.assertFalse(res["ok"])
        self.assertTrue(any("failed targets" in f for f in res["failures"]))

    def test_dynamic_reply_accepts_any_nonempty(self) -> None:
        case = {**LOCAL_CASE, "response": "Added oat milk.", "dynamic": True}
        res = evaluate(case, intent_end_event(True, speech="Added 2 oat milks."))
        self.assertTrue(res["ok"])

    def test_empty_targets_skips_target_check(self) -> None:
        case = {**LOCAL_CASE, "targets": []}
        res = evaluate(
            case,
            intent_end_event(True, success=[{"id": "todo.shopping_list"}]),
        )
        self.assertTrue(res["ok"])

    def test_llm_fallthrough_pass(self) -> None:
        res = evaluate(LLM_CASE, intent_end_event(False, speech=""))
        self.assertTrue(res["ok"])

    def test_llm_handled_locally_fails(self) -> None:
        res = evaluate(LLM_CASE, intent_end_event(True))
        self.assertFalse(res["ok"])

    def test_missing_intent_end_fails(self) -> None:
        res = evaluate(LOCAL_CASE, [{"type": "run-end", "data": None}])
        self.assertFalse(res["ok"])


if __name__ == "__main__":
    unittest.main()
