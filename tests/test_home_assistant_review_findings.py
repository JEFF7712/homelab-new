from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts.home_assistant.__main__ import (
    cmd_adopt,
    cmd_capture,
    cmd_verify,
)
from scripts.home_assistant.adapters.core import (
    CoreConfigurationAdapter,
    sync_core_to_gitops,
)
from scripts.home_assistant.adapters.dashboard import DashboardAdapter
from scripts.home_assistant.adapters.helper import HelperAdapter
from scripts.home_assistant.adapters.integration import IntegrationAdapter
from scripts.home_assistant.canonical import (
    IncludeTag,
    SecretTag,
    canonical_hash,
    sanitize_error,
    strip_volatile,
    to_json_compatible,
)
from scripts.home_assistant.client import MockHomeAssistantClient
from scripts.home_assistant.compare import compare_three_way
from scripts.home_assistant.models import (
    ActionType,
    ApplyPlan,
    BaselineRecord,
    DiffStatus,
    ExitCode,
    PlanAction,
    ResourceDocument,
)
from scripts.home_assistant.planner import LockError, Planner, StalePlanError
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
        self.allow_delete = False
        self.force = False
        self.sync_gitops = False
        self.plan_file = None
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestHomeAssistantReviewFindings(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "home-assistant" / "core").mkdir(parents=True)
        (self.root / "home-assistant" / "automations").mkdir(parents=True)
        (self.root / "home-assistant" / "scripts").mkdir(parents=True)
        (self.root / "home-assistant" / "dashboards").mkdir(parents=True)
        (self.root / "gitops" / "home-assistant").mkdir(parents=True)
        self.mock_client = MockHomeAssistantClient()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    # ------------------------------------------------------------------
    # R1: cmd_adopt rejects conflicts and dirty files
    # ------------------------------------------------------------------
    @patch("scripts.home_assistant.__main__.get_client")
    def test_r1_adopt_blocks_unresolved_conflicts(
        self, mock_get_client: object
    ) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # 1. Baseline has alias "Base Alias"
        planner = Planner(self.root, "test-instance")
        base_desired = {
            "id": "conflicted_auto",
            "alias": "Base Alias",
            "triggers": [],
            "actions": [],
        }
        base_rec = BaselineRecord(
            instance="test-instance",
            source_commit="commit1",
            content_hash="basehash",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resources={
                "automation/conflicted_auto": {
                    "canonical_hash": canonical_hash(base_desired),
                    "desired": base_desired,
                }
            },
        )
        planner.save_baseline(base_rec)

        # 2. Git has "Git Divergence"
        git_doc = ResourceDocument(
            kind="automation",
            key="conflicted_auto",
            desired={
                "id": "conflicted_auto",
                "alias": "Git Divergence",
                "triggers": [],
                "actions": [],
            },
        )
        write_resource_atomic(self.root, git_doc)

        # 3. Live HA has "Live Divergence"
        self.mock_client.automations["conflicted_auto"] = {
            "id": "conflicted_auto",
            "alias": "Live Divergence",
            "triggers": [],
            "actions": [],
        }

        # 4. Attempting to adopt must fail with conflict and preserve Git source
        adopt_args = DummyArgs(select=["automation/conflicted_auto"])
        exit_code = cmd_adopt(adopt_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(exit_code, ExitCode.CONFLICT_OR_INVALID.value)

        # Verify Git file was NOT overwritten
        auto_file = (
            self.root / "home-assistant" / "automations" / "conflicted_auto.yaml"
        )
        self.assertIn("Git Divergence", auto_file.read_text(encoding="utf-8"))
        self.assertNotIn("Live Divergence", auto_file.read_text(encoding="utf-8"))

    @patch("subprocess.run")
    @patch("scripts.home_assistant.__main__.get_client")
    def test_r1_adopt_blocks_dirty_target_file(
        self, mock_get_client: object, mock_subproc: object
    ) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # Live experiment available for adoption
        self.mock_client.automations["new_auto"] = {
            "id": "new_auto",
            "alias": "New Auto",
            "triggers": [],
            "actions": [],
        }

        # Mock git status reporting dirty working tree file
        mock_res = unittest.mock.MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = " M home-assistant/automations/new_auto.yaml\n"
        mock_subproc.return_value = mock_res  # type: ignore[attr-defined]

        adopt_args = DummyArgs(select=["automation/new_auto"])
        exit_code = cmd_adopt(adopt_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(exit_code, ExitCode.CONFLICT_OR_INVALID.value)

    # ------------------------------------------------------------------
    # R2: Preflight secret checks, file permissions, error sanitization
    # ------------------------------------------------------------------
    @patch("scripts.home_assistant.__main__.get_client")
    def test_r2_capture_and_adopt_reject_plaintext_secrets_before_write(
        self, mock_get_client: object
    ) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # Live state has plaintext credential
        self.mock_client.automations["leaky_auto"] = {
            "id": "leaky_auto",
            "alias": "Leaky Automation",
            "triggers": [],
            "actions": [
                {
                    "action": "notify.telegram",
                    "data": {"password": "super_secret_plaintext_password_123"},
                }
            ],
        }

        # 1. Adoption must be rejected before any file write
        adopt_args = DummyArgs(select=["automation/leaky_auto"])
        adopt_code = cmd_adopt(adopt_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(adopt_code, ExitCode.CONFLICT_OR_INVALID.value)
        self.assertFalse(
            (self.root / "home-assistant" / "automations" / "leaky_auto.yaml").exists()
        )

        # 2. Capture must also reject before writing capture.json
        capture_args = DummyArgs()
        capture_code = cmd_capture(capture_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(capture_code, ExitCode.CONFLICT_OR_INVALID.value)

    def test_r2_error_sanitization(self) -> None:
        sensitive_err = "Failed connection to https://user:secretpass123@ha.example.com with Bearer eyJhbGciOiJIUzI1NiJ9.abc"
        cleaned = sanitize_error(sensitive_err)
        self.assertNotIn("secretpass123", cleaned)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9.abc", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    @patch("scripts.home_assistant.__main__.get_client")
    def test_r2_capture_file_permissions(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]
        capture_args = DummyArgs()
        code = cmd_capture(capture_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(code, ExitCode.CLEAN.value)

        captures_base = (
            self.root / ".agent-state" / "home-assistant" / "test-instance" / "captures"
        )
        cap_dirs = list(captures_base.iterdir())
        self.assertTrue(len(cap_dirs) > 0)
        cap_dir = cap_dirs[0]
        dir_mode = cap_dir.stat().st_mode & 0o777
        self.assertEqual(dir_mode, 0o700)
        cap_file = cap_dir / "capture.json"
        file_mode = cap_file.stat().st_mode & 0o777
        self.assertEqual(file_mode, 0o600)

    # ------------------------------------------------------------------
    # R3: Plan bindings (target, version, baseline, source hash, TTL)
    # ------------------------------------------------------------------
    def test_r3_plan_bindings_validation(self) -> None:
        planner = Planner(self.root, "target-01")
        base_rec = BaselineRecord(
            instance="target-01",
            source_commit="rev1",
            content_hash="correct_hash",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resources={},
        )
        planner.save_baseline(base_rec)

        now = datetime.now(timezone.utc).isoformat()
        plan = ApplyPlan(
            plan_id="plan-1",
            timestamp=now,
            instance="target-01",
            git_revision="rev1",
            baseline_hash="correct_hash",
            actions=[
                PlanAction(
                    kind="automation",
                    key="foo",
                    action=ActionType.CREATE,
                    before=None,
                    after={"id": "foo", "alias": "Foo", "triggers": [], "actions": []},
                    expected_live_hash=None,
                )
            ],
            ha_version="2026.9.1",
            source_hash="source123",
        )

        git_docs = {
            "automation/foo": ResourceDocument(
                kind="automation",
                key="foo",
                desired={"id": "foo", "alias": "Foo", "triggers": [], "actions": []},
            )
        }

        # 1. Wrong instance must be rejected
        bad_inst_plan = ApplyPlan.from_dict(
            {**plan.to_dict(), "instance": "other-instance"}
        )
        with self.assertRaises(StalePlanError):
            planner.execute_plan(bad_inst_plan, self.mock_client, git_docs)

        # 2. Expired plan (> 1800s TTL) must be rejected
        expired_plan = ApplyPlan.from_dict(
            {**plan.to_dict(), "timestamp": "2020-01-01T00:00:00+00:00"}
        )
        with self.assertRaises(StalePlanError):
            planner.execute_plan(expired_plan, self.mock_client, git_docs)

        # 3. Wrong baseline hash must be rejected
        bad_base_plan = ApplyPlan.from_dict(
            {**plan.to_dict(), "baseline_hash": "wrong_hash"}
        )
        with self.assertRaises(StalePlanError):
            planner.execute_plan(bad_base_plan, self.mock_client, git_docs)

        # 4. Mismatched HA version must be rejected
        bad_ver_plan = ApplyPlan.from_dict({**plan.to_dict(), "ha_version": "2024.1.0"})
        with self.assertRaises(StalePlanError):
            planner.execute_plan(bad_ver_plan, self.mock_client, git_docs)

        # 5. Modified Git source must be rejected
        with self.assertRaises(StalePlanError):
            planner.execute_plan(plan, self.mock_client, {})  # foo missing from source

    # ------------------------------------------------------------------
    # R4: Failed reads propagate as UNKNOWN, never deleted or created
    # ------------------------------------------------------------------
    def test_r4_failed_reads_propagate_unknown(self) -> None:
        git_doc = ResourceDocument(
            kind="automation",
            key="lights",
            desired={"id": "lights", "alias": "Lights"},
        )
        # Kind-wide collection error for automations
        diff_rep = compare_three_way(
            instance="test-instance",
            baseline={"automation/lights": git_doc},
            git={"automation/lights": git_doc},
            live={},  # live returned empty due to error!
            errors={"automation/all": "Connection reset by peer"},
        )
        item = diff_rep.items[0]
        self.assertEqual(item.status, DiffStatus.UNKNOWN)
        self.assertIn("Connection reset by peer", item.details)

        # Planner refuses to plan unknown
        planner = Planner(self.root, "test-instance")
        with self.assertRaises(ValueError):
            planner.create_plan(diff_rep, git_revision="rev1", baseline_hash="base1")

    # ------------------------------------------------------------------
    # R5: Observe-only adapters reject mutation and perform real readback
    # ------------------------------------------------------------------
    def test_r5_observe_only_adapters_reject_mutation(self) -> None:
        helper = HelperAdapter()
        integration = IntegrationAdapter()
        core = CoreConfigurationAdapter()

        self.assertFalse(helper.supports_mutation)
        self.assertFalse(integration.supports_mutation)
        self.assertFalse(core.supports_mutation)

        action = PlanAction(
            kind="helper",
            key="input_boolean.test",
            action=ActionType.CREATE,
            before=None,
            after={},
            expected_live_hash=None,
        )
        with self.assertRaises(NotImplementedError):
            helper.apply(self.mock_client, action)
        with self.assertRaises(NotImplementedError):
            integration.apply(self.mock_client, action)
        with self.assertRaises(NotImplementedError):
            core.apply(self.mock_client, action)

    # ------------------------------------------------------------------
    # R6: Cluster-shared baseline
    # ------------------------------------------------------------------
    @patch("scripts.home_assistant.__main__.get_client")
    def test_r6_cluster_shared_baseline(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        # Verify command updates cluster baseline
        doc = ResourceDocument(
            kind="automation",
            key="night_light",
            desired={
                "id": "night_light",
                "alias": "Night Light",
                "triggers": [],
                "actions": [],
            },
        )
        write_resource_atomic(self.root, doc)
        self.mock_client.automations["night_light"] = doc.desired

        verify_args = DummyArgs()
        code = cmd_verify(verify_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(code, ExitCode.CLEAN.value)

        # Baseline should be saved in cluster_baselines on client
        self.assertIn("test-instance", self.mock_client.cluster_baselines)
        cluster_base = self.mock_client.cluster_baselines["test-instance"]
        self.assertIn("automation/night_light", cluster_base["resources"])

    # ------------------------------------------------------------------
    # R7: Atomic locking, renewal, release, crash recovery
    # ------------------------------------------------------------------
    def test_r7_atomic_locking(self) -> None:
        planner = Planner(self.root, "test-instance")
        planner.acquire_lock(owner="agent-1", plan_id="p1")

        # Second acquire by another agent must fail with LockError
        with self.assertRaises(LockError):
            planner.acquire_lock(owner="agent-2", plan_id="p2")

        # Lock file permissions must be 0o600
        lock_mode = planner.lock_file.stat().st_mode & 0o777
        self.assertEqual(lock_mode, 0o600)

        # Owner-checked release: wrong owner cannot release
        planner.release_lock(plan_id="p1", owner="agent-wrong")
        self.assertTrue(planner.lock_file.exists())

        # Correct owner releases
        planner.release_lock(plan_id="p1", owner="agent-1")
        self.assertFalse(planner.lock_file.exists())

    # ------------------------------------------------------------------
    # R8: Path-aware volatile filtering preserves nested user configuration
    # ------------------------------------------------------------------
    def test_r8_path_aware_volatile_filtering(self) -> None:
        user_script = {
            "alias": "My Script",
            "last_triggered": "2026-09-09T12:00:00Z",
            "sequence": [
                {
                    "variables": {
                        "context": "kitchen_motion",
                        "created_at": "custom_timestamp_param",
                    }
                }
            ],
        }

        cleaned = strip_volatile(user_script)
        self.assertNotIn("last_triggered", cleaned)
        self.assertEqual(
            cleaned["sequence"][0]["variables"]["context"], "kitchen_motion"
        )
        self.assertEqual(
            cleaned["sequence"][0]["variables"]["created_at"], "custom_timestamp_param"
        )

        script_a = {"sequence": [{"variables": {"context": "door_open"}}]}
        script_b = {"sequence": [{"variables": {"context": "window_open"}}]}
        self.assertNotEqual(canonical_hash(script_a), canonical_hash(script_b))

    # ------------------------------------------------------------------
    # R9: Adopting UI deletions with --allow-delete and dependency checks
    # ------------------------------------------------------------------
    @patch("scripts.home_assistant.__main__.get_client")
    def test_r9_adopt_ui_deletions(self, mock_get_client: object) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        doc = ResourceDocument(
            kind="automation",
            key="deleted_auto",
            desired={
                "id": "deleted_auto",
                "alias": "To Delete",
                "triggers": [],
                "actions": [],
            },
        )
        write_resource_atomic(self.root, doc)

        planner = Planner(self.root, "test-instance")
        base_rec = BaselineRecord(
            instance="test-instance",
            source_commit="c1",
            content_hash="h1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            resources={
                "automation/deleted_auto": {
                    "canonical_hash": canonical_hash(doc.desired),
                    "desired": doc.desired,
                }
            },
        )
        planner.save_baseline(base_rec)

        # 2. Adopt without --allow-delete must be rejected
        adopt_args_no_del = DummyArgs(
            select=["automation/deleted_auto"], allow_delete=False
        )
        code = cmd_adopt(adopt_args_no_del, self.root)  # type: ignore[arg-type]
        self.assertEqual(code, ExitCode.CONFLICT_OR_INVALID.value)
        self.assertTrue(
            (
                self.root / "home-assistant" / "automations" / "deleted_auto.yaml"
            ).exists()
        )

        # 3. Adopt with --allow-delete succeeds and deletes file
        adopt_args_with_del = DummyArgs(
            select=["automation/deleted_auto"], allow_delete=True
        )
        code2 = cmd_adopt(adopt_args_with_del, self.root)  # type: ignore[arg-type]
        self.assertEqual(code2, ExitCode.CLEAN.value)
        self.assertFalse(
            (
                self.root / "home-assistant" / "automations" / "deleted_auto.yaml"
            ).exists()
        )

    @patch("scripts.home_assistant.__main__.get_client")
    def test_r9_adopt_ui_deletion_blocked_by_dependency(
        self, mock_get_client: object
    ) -> None:
        mock_get_client.return_value = self.mock_client  # type: ignore[attr-defined]

        script_doc = ResourceDocument(
            kind="script",
            key="turn_off_fan",
            desired={"alias": "Turn Off Fan", "sequence": []},
        )
        write_resource_atomic(self.root, script_doc)

        auto_doc = ResourceDocument(
            kind="automation",
            key="evening",
            desired={
                "id": "evening",
                "alias": "Evening",
                "triggers": [],
                "actions": [{"action": "script.turn_off_fan"}],
            },
        )
        write_resource_atomic(self.root, auto_doc)

        planner = Planner(self.root, "test-instance")
        planner.save_baseline(
            BaselineRecord(
                instance="test-instance",
                source_commit="c1",
                content_hash="h1",
                timestamp=datetime.now(timezone.utc).isoformat(),
                resources={
                    "script/turn_off_fan": {
                        "canonical_hash": canonical_hash(script_doc.desired),
                        "desired": script_doc.desired,
                    }
                },
            )
        )

        adopt_args = DummyArgs(select=["script/turn_off_fan"], allow_delete=True)
        code = cmd_adopt(adopt_args, self.root)  # type: ignore[arg-type]
        self.assertEqual(code, ExitCode.CONFLICT_OR_INVALID.value)
        self.assertTrue(
            (self.root / "home-assistant" / "scripts" / "turn_off_fan.yaml").exists()
        )

    # ------------------------------------------------------------------
    # R10: Dashboard metadata reconciliation and verification
    # ------------------------------------------------------------------
    def test_r10_dashboard_metadata_reconciliation(self) -> None:
        adapter = DashboardAdapter()
        self.mock_client.create_dashboard(
            url_path="analytics",
            title="Old Analytics Title",
            icon="mdi:chart-line",
            show_in_sidebar=True,
        )

        desired_doc = ResourceDocument(
            kind="dashboard",
            key="analytics",
            desired={
                "title": "New Analytics Title",
                "icon": "mdi:chart-bar",
                "show_in_sidebar": True,
                "require_admin": False,
                "views": [],
            },
        )

        action = PlanAction(
            kind="dashboard",
            key="analytics",
            action=ActionType.UPDATE,
            before={"title": "Old Analytics Title"},
            after=desired_doc.desired,
            expected_live_hash=None,
        )
        adapter.apply(self.mock_client, action)

        meta_after = next(
            d for d in self.mock_client.dashboard_list if d.get("id") == "analytics"
        )
        self.assertEqual(meta_after["title"], "New Analytics Title")
        self.assertEqual(meta_after["icon"], "mdi:chart-bar")
        self.assertTrue(adapter.verify(self.mock_client, desired_doc))

    # ------------------------------------------------------------------
    # R11: Core source synchronization to GitOps ConfigMap
    # ------------------------------------------------------------------
    def test_r11_core_gitops_synchronization(self) -> None:
        core_yaml = "default_config:\nrecorder:\n  db_url: !secret recorder_db_url\n"
        core_file = self.root / "home-assistant" / "core" / "configuration.yaml"
        core_file.write_text(core_yaml, encoding="utf-8")

        dep_yaml = (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  annotations:\n"
            "    checksum/config: 1111111111111111111111111111111111111111111111111111111111111111\n"
        )
        dep_file = self.root / "gitops" / "home-assistant" / "deployment.yaml"
        dep_file.write_text(dep_yaml, encoding="utf-8")

        sync_core_to_gitops(self.root)

        cm_file = self.root / "gitops" / "home-assistant" / "config.yaml"
        self.assertTrue(cm_file.is_file())
        self.assertIn("default_config:", cm_file.read_text(encoding="utf-8"))

        new_dep_text = dep_file.read_text(encoding="utf-8")
        self.assertNotIn(
            "1111111111111111111111111111111111111111111111111111111111111111",
            new_dep_text,
        )

    # ------------------------------------------------------------------
    # R12: Safe serialization of SecretTag and IncludeTag
    # ------------------------------------------------------------------
    def test_r12_tag_serialization(self) -> None:
        data = {
            "recorder": {"db_url": SecretTag("my_secret")},
            "automations": IncludeTag("automations.yaml"),
        }
        json_ready = to_json_compatible(data)
        self.assertEqual(json_ready["recorder"]["db_url"], {"!secret": "my_secret"})
        self.assertEqual(json_ready["automations"], {"!include": "automations.yaml"})

        doc = ResourceDocument(kind="core", key="configuration", desired=data)
        doc_dict = doc.to_dict()
        self.assertEqual(
            doc_dict["desired"]["recorder"]["db_url"], {"!secret": "my_secret"}
        )

        action = PlanAction(
            kind="core",
            key="configuration",
            action=ActionType.UPDATE,
            before=None,
            after=data,
            expected_live_hash=None,
        )
        act_dict = action.to_dict()
        self.assertEqual(
            act_dict["after"]["recorder"]["db_url"], {"!secret": "my_secret"}
        )


if __name__ == "__main__":
    unittest.main()
