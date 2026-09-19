from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.home_assistant.__main__ import (
    cmd_adopt,
    cmd_apply,
    cmd_diff,
    cmd_plan,
    cmd_revert,
    cmd_validate,
    cmd_verify,
)
from scripts.home_assistant.client import MockHomeAssistantClient
from scripts.home_assistant.models import (
    ExitCode,
    ResourceDocument,
)
from scripts.home_assistant.planner import Planner
from scripts.home_assistant.source import write_resource_atomic


class DummyArgs:
    def __init__(self, **kwargs: object) -> None:
        self.instance = "test-instance"
        self.json = True
        self.mock = True
        self.url = None
        self.token = None
        self.token_file = None
        self.select = None
        self.all = False
        self.plan_file = None
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestHomeAssistantCLI(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "home-assistant" / "core").mkdir(parents=True)
        (self.root / "home-assistant" / "automations").mkdir(parents=True)
        (self.root / "home-assistant" / "dashboards").mkdir(parents=True)
        self.mock_client = MockHomeAssistantClient()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @patch("scripts.home_assistant.__main__.get_client")
    def test_workflow_a_natural_language_agent_change(
        self, mock_get_client: object
    ) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # 1. Agent authors desired automation in Git
        doc = ResourceDocument(
            kind="automation",
            key="bedtime",
            desired={
                "id": "bedtime",
                "alias": "Bedtime Routine",
                "trigger": [{"platform": "time", "at": "22:00:00"}],
                "action": [
                    {"action": "light.turn_off", "target": {"entity_id": "light.all"}}
                ],
            },
        )
        write_resource_atomic(self.root, doc)

        # 2. Validate
        val_args = DummyArgs()
        val_code = cmd_validate(val_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(val_code, ExitCode.CLEAN.value)

        # 3. Diff shows GIT_CHANGE
        diff_args = DummyArgs()
        diff_code = cmd_diff(diff_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(diff_code, ExitCode.DRIFT_OR_PENDING.value)

        # 4. Plan
        plan_args = DummyArgs(select=["automation/bedtime"])
        plan_code = cmd_plan(plan_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(plan_code, ExitCode.CLEAN.value)

        # 5. Apply
        apply_args = DummyArgs(select=["automation/bedtime"])
        apply_code = cmd_apply(apply_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(apply_code, ExitCode.CLEAN.value)

        # Verify mutation landed in HA
        self.assertIn("bedtime", self.mock_client.automations)
        self.assertEqual(
            self.mock_client.automations["bedtime"]["alias"], "Bedtime Routine"
        )

        # 6. Verify readback
        verify_args = DummyArgs()
        verify_code = cmd_verify(verify_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(verify_code, ExitCode.CLEAN.value)

        # 7. Diff for this automation is now clean!
        clean_code = cmd_diff(DummyArgs(select=["automation/bedtime"]), self.root)  # type: ignore[arg-type]
        self.assertEqual(clean_code, ExitCode.CLEAN.value)

    @patch("scripts.home_assistant.__main__.get_client")
    def test_workflow_b_ui_experiment_adoption(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # 1. User experiments in UI (creates an automation in HA directly)
        self.mock_client.automations["sunset_lights"] = {
            "id": "sunset_lights",
            "alias": "Sunset Lights",
            "trigger": [{"platform": "sun", "event": "sunset"}],
            "action": [{"action": "light.turn_on"}],
        }
        self.mock_client.entities.append(
            {"entity_id": "automation.sunset_lights", "unique_id": "sunset_lights"}
        )

        # 2. Diff shows EXPERIMENT
        diff_args = DummyArgs()
        diff_code = cmd_diff(diff_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(diff_code, ExitCode.DRIFT_OR_PENDING.value)

        # 3. User asks to adopt UI changes
        adopt_args = DummyArgs(select=["automation/sunset_lights"])
        adopt_code = cmd_adopt(adopt_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(adopt_code, ExitCode.CLEAN.value)

        # 4. Verify local Git source now contains the file
        git_file = self.root / "home-assistant" / "automations" / "sunset_lights.yaml"
        self.assertTrue(git_file.is_file())

        # Baseline did NOT advance yet!
        planner = Planner(self.root, "test-instance")
        baseline = planner.load_baseline()
        if baseline:
            self.assertNotIn("automation/sunset_lights", baseline.resources)

        # 5. Validate source
        val_code = cmd_validate(DummyArgs(), self.root)  # type: ignore[arg-type]
        self.assertEqual(val_code, ExitCode.CLEAN.value)

    @patch("scripts.home_assistant.__main__.get_client")
    def test_stale_plan_rejection(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # Existing automation in both Git and HA
        doc = ResourceDocument(
            kind="automation",
            key="light_toggle",
            desired={
                "id": "light_toggle",
                "alias": "Initial Alias",
                "trigger": [],
                "action": [],
            },
        )
        write_resource_atomic(self.root, doc)
        self.mock_client.automations["light_toggle"] = {
            "id": "light_toggle",
            "alias": "Initial Alias",
            "trigger": [],
            "action": [],
        }

        # Initialize baseline with Initial Alias
        planner = Planner(self.root, "test-instance")
        from scripts.home_assistant.canonical import canonical_hash
        from scripts.home_assistant.compare import compare_three_way
        from scripts.home_assistant.models import BaselineRecord

        baseline_rec = BaselineRecord(
            instance="test-instance",
            source_commit="git1",
            content_hash="base1",
            timestamp="2026-09-09T00:00:00Z",
            resources={
                "automation/light_toggle": {
                    "canonical_hash": canonical_hash(doc.desired),
                    "desired": doc.desired,
                }
            },
        )
        planner.save_baseline(baseline_rec)

        # User changes Git to "New Git Alias"
        doc_updated = ResourceDocument(
            kind="automation",
            key="light_toggle",
            desired={
                "id": "light_toggle",
                "alias": "New Git Alias",
                "trigger": [],
                "action": [],
            },
        )
        write_resource_atomic(self.root, doc_updated)

        # Diff report
        diff_report = compare_three_way(
            instance="test-instance",
            baseline={"automation/light_toggle": doc},
            git={"automation/light_toggle": doc_updated},
            live={"automation/light_toggle": doc},
        )

        # Plan generated with expected live hash of "Initial Alias"
        plan = planner.create_plan(
            diff_report=diff_report,
            git_revision="git2",
            baseline_hash="base1",
            selected_keys={"automation/light_toggle"},
        )

        # BUT before apply, live HA UI was edited by user to "UI Sneak Edit"!
        self.mock_client.automations["light_toggle"]["alias"] = "UI Sneak Edit"

        # Apply must fail with StalePlanError!
        with self.assertRaises(Exception):
            planner.execute_plan(
                plan, self.mock_client, {"automation/light_toggle": doc_updated}
            )

    @patch("scripts.home_assistant.__main__.get_client")
    def test_revert_workflow(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # Accepted Git state
        doc = ResourceDocument(
            kind="automation",
            key="fan_control",
            desired={
                "id": "fan_control",
                "alias": "Git Fan",
                "trigger": [],
                "action": [],
            },
        )
        write_resource_atomic(self.root, doc)

        # Live UI diverged
        self.mock_client.automations["fan_control"] = {
            "id": "fan_control",
            "alias": "Messed Up Live UI",
            "trigger": [],
            "action": [],
        }

        # Explicit revert command
        revert_args = DummyArgs(select=["automation/fan_control"])
        revert_code = cmd_revert(revert_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(revert_code, ExitCode.CLEAN.value)

        # Live UI is restored to Git Fan!
        self.assertEqual(
            self.mock_client.automations["fan_control"]["alias"], "Git Fan"
        )

    @patch("scripts.home_assistant.__main__.get_client")
    def test_validate_warns_on_unknown_kind_without_failing_pipeline(
        self, mock_get_client: object
    ) -> None:
        """A single resource with a typo'd kind must not block the validate
        pass for every other resource. The bad kind is reported in
        skipped_unknown_kind so the operator can see and fix it."""
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # One well-formed automation
        write_resource_atomic(
            self.root,
            ResourceDocument(
                kind="automation",
                key="bedtime",
                desired={
                    "id": "bedtime",
                    "alias": "Bedtime",
                    "trigger": [{"platform": "time", "at": "22:00:00"}],
                    "action": [],
                },
            ),
        )

        # One resource whose `kind` is not a registered adapter (typo or
        # live-data bleed). We write a file that the loader will see; the
        # kind we record is what trips try_get_adapter.
        from scripts.home_assistant.source import get_source_path

        bad_path = get_source_path(self.root, "entitie", "foo")
        bad_path.parent.mkdir(parents=True, exist_ok=True)
        bad_path.write_text(
            "id: foo\nalias: typo'd kind\n",
            encoding="utf-8",
        )

        val_args = DummyArgs()
        val_code = cmd_validate(val_args, self.root)  # type: ignore[arg-type]
        # CLEAN, not BLOCKED: the unknown kind is a warning, not a failure.
        self.assertEqual(val_code, ExitCode.CLEAN.value)

    def test_try_get_adapter_returns_none_for_unknown_kind(self) -> None:
        from scripts.home_assistant.adapters import (
            get_adapter,
            try_get_adapter,
        )

        self.assertIsNotNone(try_get_adapter("automation"))
        self.assertIsNone(try_get_adapter("entitie"))
        with self.assertRaises(ValueError):
            get_adapter("entitie")

    def test_verify_summary_counts_drifted_per_surface(self) -> None:
        from scripts.home_assistant.__main__ import build_verify_summary

        git = {
            "automation/a": ResourceDocument(
                kind="automation", key="a", desired={"id": "a"}
            ),
            "automation/b": ResourceDocument(
                kind="automation", key="b", desired={"id": "b"}
            ),
            "script/s": ResourceDocument(
                kind="script", key="s", desired={"alias": "S"}
            ),
        }
        live = {
            "automation/a": ResourceDocument(
                kind="automation", key="a", desired={"id": "a"}
            ),
            "automation/c": ResourceDocument(
                kind="automation", key="c", desired={"id": "c"}
            ),
        }
        summary = build_verify_summary(git, ["automation/b"], live)

        auto_row = next(s for s in summary["surfaces"] if s["kind"] == "automation")
        self.assertEqual(
            (auto_row["managed"], auto_row["converged"], auto_row["drifted"]),
            (2, 1, 1),
        )
        self.assertEqual(auto_row["unmanaged"], 1)
        self.assertIn("automation/c", summary["unmanaged"])
        self.assertEqual(
            (summary["managed_total"], summary["managed_converged"]),
            (3, 2),
        )

    @patch("scripts.home_assistant.__main__.get_client")
    def test_verify_reports_unmanaged_without_failing(
        self, mock_get_client: object
    ) -> None:
        import io
        import json
        from contextlib import redirect_stdout

        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        desired = {
            "id": "bedtime",
            "alias": "Bedtime Routine",
            "trigger": [],
            "action": [],
        }
        write_resource_atomic(
            self.root,
            ResourceDocument(kind="automation", key="bedtime", desired=desired),
        )
        self.mock_client.automations["bedtime"] = dict(desired)
        self.mock_client.automations["ui_experiment"] = {
            "id": "ui_experiment",
            "alias": "UI Experiment",
            "trigger": [],
            "action": [],
        }

        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cmd_verify(DummyArgs(), self.root)  # type: ignore[arg-type]
        self.assertEqual(code, ExitCode.CLEAN.value)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "verified")
        self.assertIn("automation/ui_experiment", payload["unmanaged"])
        auto_row = next(s for s in payload["surfaces"] if s["kind"] == "automation")
        self.assertEqual(auto_row["managed"], 1)
        self.assertEqual(auto_row["converged"], 1)
        self.assertEqual(auto_row["drifted"], 0)
        self.assertEqual(auto_row["unmanaged"], 1)


if __name__ == "__main__":
    unittest.main()
