"""Planner behavior for observe-only resources with Git drift.

A full plan must skip observe-only GIT_CHANGE items (recording them) instead
of failing the whole run. An explicitly selected observe-only resource must
still raise.
"""

import tempfile
import unittest
from pathlib import Path

from scripts.home_assistant.models import (
    ComparisonItem,
    DiffReport,
    DiffStatus,
)
from scripts.home_assistant.planner import Planner


def _report() -> DiffReport:
    return DiffReport(
        instance="test-instance",
        timestamp="2026-01-01T00:00:00+00:00",
        items=[
            ComparisonItem(
                kind="helper",
                key="input_boolean_guest_mode",
                status=DiffStatus.GIT_CHANGE,
                git={"name": "Guest mode"},
                live={"name": "Guest mode (edited)"},
            ),
            ComparisonItem(
                kind="automation",
                key="some_auto",
                status=DiffStatus.GIT_CHANGE,
                git={"alias": "Some Auto"},
                live={"alias": "Some Auto (old)"},
            ),
        ],
    )


class ObserveOnlyPlanTest(unittest.TestCase):
    def _planner(self) -> Planner:
        return Planner(Path(tempfile.mkdtemp()), "test-instance", client=None)

    def test_full_plan_skips_observe_only(self) -> None:
        plan = self._planner().create_plan(
            diff_report=_report(),
            git_revision="abc",
            baseline_hash="base",
        )
        self.assertEqual([a.key for a in plan.actions], ["some_auto"])
        self.assertEqual(plan.skipped, ["helper/input_boolean_guest_mode"])
        round_tripped = plan.to_dict()
        self.assertEqual(
            round_tripped["skipped"], ["helper/input_boolean_guest_mode"]
        )
        from scripts.home_assistant.models import ApplyPlan

        self.assertEqual(
            ApplyPlan.from_dict(round_tripped).skipped,
            ["helper/input_boolean_guest_mode"],
        )

    def test_explicit_select_still_raises(self) -> None:
        with self.assertRaises(ValueError):
            self._planner().create_plan(
                diff_report=_report(),
                git_revision="abc",
                baseline_hash="base",
                selected_keys={"helper/input_boolean_guest_mode"},
            )


if __name__ == "__main__":
    unittest.main()
