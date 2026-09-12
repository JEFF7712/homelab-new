from __future__ import annotations

import unittest

from scripts.home_assistant.adapters.automation import AutomationAdapter
from scripts.home_assistant.adapters.core import CoreConfigurationAdapter
from scripts.home_assistant.adapters.dashboard import DashboardAdapter
from scripts.home_assistant.adapters.registry import (
    AreaRegistryAdapter,
    LabelRegistryAdapter,
)
from scripts.home_assistant.adapters.scene import SceneAdapter
from scripts.home_assistant.adapters.script import ScriptAdapter
from scripts.home_assistant.client import MockHomeAssistantClient
from scripts.home_assistant.models import ActionType, PlanAction, ResourceDocument


class TestHomeAssistantAdapters(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MockHomeAssistantClient()

    def test_automation_adapter_crud(self) -> None:
        adapter = AutomationAdapter()
        action_create = PlanAction(
            kind="automation",
            key="test_auto",
            action=ActionType.CREATE,
            after={
                "id": "test_auto",
                "alias": "Test Automation",
                "trigger": [{"platform": "time", "at": "08:00:00"}],
                "action": [{"action": "light.turn_on"}],
            },
        )
        adapter.apply(self.client, action_create)
        self.assertIn("test_auto", self.client.automations)

        doc = ResourceDocument(
            kind="automation",
            key="test_auto",
            desired=self.client.automations["test_auto"],
        )
        self.assertTrue(adapter.verify(self.client, doc))

        # Delete
        action_del = PlanAction(
            kind="automation", key="test_auto", action=ActionType.DELETE
        )
        adapter.apply(self.client, action_del)
        self.assertNotIn("test_auto", self.client.automations)
        self.assertFalse(adapter.verify(self.client, doc))

    def test_script_adapter_crud(self) -> None:
        adapter = ScriptAdapter()
        action = PlanAction(
            kind="script",
            key="goodnight",
            action=ActionType.CREATE,
            after={"alias": "Goodnight", "sequence": [{"action": "light.turn_off"}]},
        )
        adapter.apply(self.client, action)
        self.assertIn("goodnight", self.client.scripts)
        doc = ResourceDocument(
            kind="script", key="goodnight", desired=self.client.scripts["goodnight"]
        )
        self.assertTrue(adapter.verify(self.client, doc))

    def test_scene_adapter_crud(self) -> None:
        adapter = SceneAdapter()
        action = PlanAction(
            kind="scene",
            key="movie_time",
            action=ActionType.CREATE,
            after={
                "name": "Movie Time",
                "entities": {"light.living_room": {"state": "off"}},
            },
        )
        adapter.apply(self.client, action)
        self.assertIn("movie_time", self.client.scenes)
        doc = ResourceDocument(
            kind="scene", key="movie_time", desired=self.client.scenes["movie_time"]
        )
        self.assertTrue(adapter.verify(self.client, doc))

    def test_dashboard_adapter_preserves_card_and_view_order(self) -> None:
        adapter = DashboardAdapter()
        desired_dashboard = {
            "title": "Living Dashboard",
            "icon": "mdi:home",
            "require_admin": False,
            "show_in_sidebar": True,
            "views": [
                {
                    "title": "Main",
                    "cards": [
                        {
                            "type": "entities",
                            "entities": ["light.living_room", "light.kitchen"],
                        },
                        {"type": "weather-forecast", "entity": "weather.home"},
                    ],
                },
                {
                    "title": "Media",
                    "cards": [{"type": "media-control", "entity": "media_player.tv"}],
                },
            ],
        }
        action = PlanAction(
            kind="dashboard",
            key="living",
            action=ActionType.CREATE,
            after=desired_dashboard,
        )
        adapter.apply(self.client, action)
        self.assertIn("living", self.client.dashboards)

        live_conf = self.client.get_dashboard_config("living")
        self.assertEqual(len(live_conf["views"]), 2)
        self.assertEqual(live_conf["views"][0]["title"], "Main")
        self.assertEqual(live_conf["views"][0]["cards"][0]["type"], "entities")
        self.assertEqual(live_conf["views"][0]["cards"][1]["type"], "weather-forecast")

        doc = ResourceDocument(
            kind="dashboard", key="living", desired=desired_dashboard
        )
        self.assertTrue(adapter.verify(self.client, doc))

    def test_registry_allowlist_filtering(self) -> None:
        area_adapter = AreaRegistryAdapter()
        self.client.areas = [
            {
                "area_id": "kitchen",
                "name": "Kitchen",
                "icon": "mdi:silverware",
                "floor_id": None,
                "aliases": [],
                "unwanted_runtime_field": 12345,
            }
        ]
        exported = area_adapter.export_from_live(self.client)
        self.assertEqual(len(exported), 1)
        area_item = exported[0].desired[0]
        self.assertEqual(area_item["name"], "Kitchen")
        self.assertNotIn("unwanted_runtime_field", area_item)

    def test_label_adapter_crud(self) -> None:
        adapter = LabelRegistryAdapter()
        action_create = PlanAction(
            kind="label",
            key="collection",
            action=ActionType.CREATE,
            after=[
                {
                    "label_id": "shared_space",
                    "name": "Shared Space",
                    "icon": "mdi:home-group",
                    "description": "Lighting in areas shared by all residents.",
                }
            ],
        )
        adapter.apply(self.client, action_create)
        self.assertEqual(len(self.client.labels), 1)
        self.assertEqual(self.client.labels[0]["label_id"], "shared_space")

        doc = ResourceDocument(
            kind="label", key="collection", desired=self.client.labels
        )
        self.assertEqual(adapter.validate(doc), [])
        self.assertTrue(adapter.verify(self.client, doc))

        action_update = PlanAction(
            kind="label",
            key="collection",
            action=ActionType.UPDATE,
            after=[
                {
                    "label_id": "shared_space",
                    "name": "Shared Space",
                    "icon": "mdi:home-floor-1",
                }
            ],
        )
        adapter.apply(self.client, action_update)
        self.assertEqual(self.client.labels[0]["icon"], "mdi:home-floor-1")

    def test_label_adapter_export_filters_allowlisted_fields(self) -> None:
        adapter = LabelRegistryAdapter()
        self.client.labels = [
            {
                "label_id": "shared_space",
                "name": "Shared Space",
                "icon": "mdi:home-group",
                "color": "red",
                "description": "...",
                "unwanted_runtime_field": 9999,
            }
        ]
        exported = adapter.export_from_live(self.client)
        self.assertEqual(len(exported), 1)
        item = exported[0].desired[0]
        self.assertEqual(item["label_id"], "shared_space")
        self.assertNotIn("unwanted_runtime_field", item)

    def test_label_adapter_validates_duplicates(self) -> None:
        adapter = LabelRegistryAdapter()
        doc = ResourceDocument(
            kind="label",
            key="collection",
            desired=[
                {"label_id": "shared_space", "name": "Shared Space"},
                {"label_id": "shared_space", "name": "Dup"},
            ],
        )
        errors = adapter.validate(doc)
        self.assertTrue(any("Duplicate label_id" in e for e in errors))

    def test_core_configuration_adapter(self) -> None:
        adapter = CoreConfigurationAdapter()
        exported = adapter.export_from_live(self.client)
        self.assertEqual(len(exported), 1)
        self.assertEqual(exported[0].kind, "core")
        self.assertEqual(exported[0].key, "configuration")
        self.assertEqual(adapter.validate(exported[0]), [])
        self.assertTrue(adapter.verify(self.client, exported[0]))


if __name__ == "__main__":
    unittest.main()
