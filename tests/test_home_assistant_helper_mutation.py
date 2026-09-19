"""Helper name/icon mutation via the entity registry.

Helpers are ui-editable: name and icon overrides are written with
``config/entity_registry/update`` (the same call the HA frontend uses).
Create/delete remain UI operations because the registry API can neither
provision nor remove the underlying helper.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.home_assistant.adapters.helper import HelperAdapter
from scripts.home_assistant.client import MockHomeAssistantClient
from scripts.home_assistant.models import (
    ActionType,
    ComparisonItem,
    DiffReport,
    DiffStatus,
    ExitCode,
    PlanAction,
    ResourceDocument,
)
from scripts.home_assistant.planner import Planner
from scripts.home_assistant.source import write_resource_atomic

GIT_DESIRED = {
    "entity_id": "input_boolean.guest_mode",
    "name": "Guest Mode",
    "icon": "mdi:account-multiple",
}

LIVE_ENTITY = {
    "entity_id": "input_boolean.guest_mode",
    "name": "Guest Mode",
    "icon": None,
    "original_name": None,
    "original_icon": None,
}


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


class HelperMutationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "home-assistant" / "helpers").mkdir(parents=True)
        self.client = MockHomeAssistantClient()
        self.adapter = HelperAdapter()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_git_change_plans_update_not_skip(self) -> None:
        report = DiffReport(
            instance="test-instance",
            timestamp="2026-01-01T00:00:00+00:00",
            items=[
                ComparisonItem(
                    kind="helper",
                    key="input_boolean_guest_mode",
                    status=DiffStatus.GIT_CHANGE,
                    baseline_hash="b",
                    git_hash="g",
                    live_hash="l",
                    git=dict(GIT_DESIRED),
                    live=dict(LIVE_ENTITY),
                ),
            ],
        )
        plan = Planner(self.root, "test-instance").create_plan(
            diff_report=report,
            git_revision="abc",
            baseline_hash="base",
        )
        self.assertEqual(plan.skipped, [])
        self.assertEqual(len(plan.actions), 1)
        self.assertEqual(plan.actions[0].action, ActionType.UPDATE)
        self.assertEqual(plan.actions[0].expected_live_hash, "l")

    def test_update_sets_name_and_icon_override(self) -> None:
        self.client.entities = [dict(LIVE_ENTITY)]
        self.adapter.apply(
            self.client,
            PlanAction(
                kind="helper",
                key="input_boolean_guest_mode",
                action=ActionType.UPDATE,
                before=dict(LIVE_ENTITY),
                after=dict(GIT_DESIRED),
            ),
        )
        self.assertEqual(self.client.entities[0]["icon"], "mdi:account-multiple")
        doc = ResourceDocument(
            kind="helper", key="input_boolean_guest_mode", desired=dict(GIT_DESIRED)
        )
        self.assertTrue(self.adapter.verify(self.client, doc))

    def test_update_with_none_clears_override(self) -> None:
        self.client.entities = [
            {
                "entity_id": "input_boolean.guest_mode",
                "name": "Guests",
                "icon": "mdi:party-popper",
                "original_name": "Guest Mode",
                "original_icon": None,
            }
        ]
        cleared = {
            "entity_id": "input_boolean.guest_mode",
            "name": None,
            "icon": None,
        }
        self.adapter.apply(
            self.client,
            PlanAction(
                kind="helper",
                key="input_boolean_guest_mode",
                action=ActionType.UPDATE,
                after=cleared,
            ),
        )
        self.assertIsNone(self.client.entities[0]["name"])
        self.assertIsNone(self.client.entities[0]["icon"])

    def test_create_and_delete_raise_with_guidance(self) -> None:
        with self.assertRaises(NotImplementedError) as ctx_create:
            self.adapter.apply(
                self.client,
                PlanAction(
                    kind="helper",
                    key="input_boolean_new",
                    action=ActionType.CREATE,
                    after=dict(GIT_DESIRED),
                ),
            )
        self.assertIn("Home Assistant UI", str(ctx_create.exception))
        with self.assertRaises(NotImplementedError) as ctx_delete:
            self.adapter.apply(
                self.client,
                PlanAction(
                    kind="helper",
                    key="input_boolean_guest_mode",
                    action=ActionType.DELETE,
                ),
            )
        self.assertIn("Home Assistant UI", str(ctx_delete.exception))

    @patch("scripts.home_assistant.__main__.get_client")
    def test_revert_resolves_icon_conflict(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.client  # type: ignore[attr-defined]
        from scripts.home_assistant.__main__ import cmd_revert, cmd_verify

        write_resource_atomic(
            self.root,
            ResourceDocument(
                kind="helper",
                key="input_boolean_guest_mode",
                desired=dict(GIT_DESIRED),
            ),
        )
        self.client.entities = [dict(LIVE_ENTITY)]

        revert_code = cmd_revert(  # type: ignore[arg-type]
            DummyArgs(select=["helper/input_boolean_guest_mode"]), self.root
        )
        self.assertEqual(revert_code, ExitCode.CLEAN.value)
        self.assertEqual(self.client.entities[0]["icon"], "mdi:account-multiple")

        verify_code = cmd_verify(DummyArgs(), self.root)  # type: ignore[arg-type]
        self.assertEqual(verify_code, ExitCode.CLEAN.value)


if __name__ == "__main__":
    unittest.main()
