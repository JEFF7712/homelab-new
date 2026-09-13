from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.agent_workspaces.acceptance import (
    collect_host_health,
    run_two_guest_acceptance,
)
from scripts.agent_workspaces.core import WorkspaceError, load_manifest
from tests.test_agent_workspaces import enabled_workspace, test_manifest


class HealthRunner:
    def __call__(self, command, **kwargs):
        del kwargs
        command = list(command)
        if command[:2] == ["systemctl", "show"]:
            return subprocess.CompletedProcess(
                command,
                0,
                "CPUUsageNSec=123\nMemoryCurrent=1000\nMemoryPeak=2000\nCPUQuotaPerSecUSec=2s\nMemoryHigh=9663676416\nMemoryMax=10737418240\nManagedOOMMemoryPressure=kill\n",
                "",
            )
        if command[-4:] == ["get", "nodes", "-o", "json"]:
            output = {
                "items": [
                    {
                        "metadata": {"name": "homelab-01"},
                        "status": {
                            "conditions": [
                                {"type": "Ready", "status": "True"},
                                {"type": "EtcdIsVoter", "status": "True"},
                                {"type": "MemoryPressure", "status": "False"},
                                {"type": "DiskPressure", "status": "False"},
                                {"type": "PIDPressure", "status": "False"},
                            ]
                        },
                    }
                ]
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(output), "")
        if "--raw=/readyz" in command:
            return subprocess.CompletedProcess(command, 0, "ok\n", "")
        if "deployment/home-assistant-postgres" in command:
            return subprocess.CompletedProcess(command, 0, "1\n", "")
        if command[0] == "curl":
            return subprocess.CompletedProcess(command, 0, "200", "")
        if command[0] == "ssh":
            return subprocess.CompletedProcess(
                command,
                0,
                '{"disk_bytes":1073741824,"disk_seconds":1,"rx_bytes":2,"tx_bytes":3}',
                "",
            )
        raise AssertionError(command)


def acceptance_workspaces(directory: str):
    first = enabled_workspace("acceptance-a")
    second = enabled_workspace("acceptance-b")
    second["owner"] = "acceptance-b@example.test"
    second["browser_identity"] = "acceptance-b@example.test"
    second["network"] = {
        **second["network"],
        "segment": "198.51.100.0/30",
        "address": "198.51.100.2/30",
        "gateway": "198.51.100.1",
        "mac": "02:00:00:00:00:02",
        "bridge": "aw-accept-b-br",
        "tap": "aw-accept-b-tp",
    }
    for item in (first, second):
        workspace_id = item["id"]
        item["storage"] = {
            "system_disk": f"/persist/agent-workspaces/{workspace_id}/disks/system.qcow2",
            "system_disk_gib": 16,
            "data_disk": f"/persist/agent-workspaces/{workspace_id}/disks/data.qcow2",
            "data_disk_gib": 16,
        }
    manifest = pathlib.Path(directory) / "manifest.json"
    manifest.write_text(json.dumps(test_manifest([first, second])))
    return load_manifest(manifest)


class AcceptanceTests(unittest.TestCase):
    def test_collect_health_requires_ready_etcd_postgres_and_ha(self) -> None:
        health = collect_host_health(HealthRunner())
        self.assertEqual(health["nodes"]["ready"], 1)
        self.assertEqual(health["etcd"]["voters"], 1)
        self.assertEqual(health["postgres"]["query"], "SELECT 1")
        self.assertEqual(health["home_assistant"]["http_status"], 200)
        self.assertEqual(health["workspace_slice"]["cpu_quota_per_second"], "2s")
        self.assertEqual(health["workspace_slice"]["memory_peak_bytes"], 2000)

    def test_two_guest_acceptance_records_health_and_deprovisions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspaces = acceptance_workspaces(directory)
            key = pathlib.Path(directory) / "id_ed25519"
            key.write_text("private")
            evidence = pathlib.Path(directory) / "evidence.json"
            status = {"consistent": True, "domain_state": "running"}
            with (
                patch("scripts.agent_workspaces.acceptance.os.geteuid", return_value=0),
                patch(
                    "scripts.agent_workspaces.acceptance.provision_status",
                    return_value=status,
                ),
                patch(
                    "scripts.agent_workspaces.acceptance.deprovision_workspace"
                ) as deprovision,
                patch("scripts.agent_workspaces.acceptance.time.sleep"),
            ):
                result = run_two_guest_acceptance(
                    workspaces,
                    ssh_key=key,
                    network_url="https://example.test/pressure",
                    duration_seconds=10,
                    evidence_path=evidence,
                    runner=HealthRunner(),
                )
            self.assertEqual(result["result"], "accepted")
            self.assertEqual(set(result["health"]), {"before", "during", "after"})
            self.assertIsInstance(result["health"]["during"], list)
            self.assertEqual(deprovision.call_count, 2)
            self.assertEqual(json.loads(evidence.read_text())["result"], "accepted")

    def test_acceptance_rejects_non_disposable_ids_and_unsafe_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspaces = acceptance_workspaces(directory)
            key = pathlib.Path(directory) / "id_ed25519"
            key.write_text("private")
            workspaces[0].raw["id"] = "production-user"
            with self.assertRaisesRegex(WorkspaceError, "acceptance-\\*"):
                run_two_guest_acceptance(
                    workspaces,
                    ssh_key=key,
                    network_url="https://example.test/pressure",
                    duration_seconds=10,
                    evidence_path=pathlib.Path(directory) / "evidence.json",
                    runner=HealthRunner(),
                )
            workspaces[0].raw["id"] = "acceptance-a"
            with (
                patch("scripts.agent_workspaces.acceptance.os.geteuid", return_value=0),
                self.assertRaisesRegex(WorkspaceError, "absolute HTTPS"),
            ):
                run_two_guest_acceptance(
                    workspaces,
                    ssh_key=key,
                    network_url="http://example.test;false",
                    duration_seconds=10,
                    evidence_path=pathlib.Path(directory) / "evidence.json",
                    runner=HealthRunner(),
                )

    def test_cleanup_failure_prevents_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspaces = acceptance_workspaces(directory)
            key = pathlib.Path(directory) / "id_ed25519"
            key.write_text("private")
            evidence = pathlib.Path(directory) / "evidence.json"
            status = {"consistent": True, "domain_state": "running"}
            with (
                patch("scripts.agent_workspaces.acceptance.os.geteuid", return_value=0),
                patch(
                    "scripts.agent_workspaces.acceptance.provision_status",
                    return_value=status,
                ),
                patch(
                    "scripts.agent_workspaces.acceptance.deprovision_workspace",
                    side_effect=WorkspaceError("destroy failed"),
                ),
                patch("scripts.agent_workspaces.acceptance.time.sleep"),
                self.assertRaisesRegex(WorkspaceError, "cleanup failed"),
            ):
                run_two_guest_acceptance(
                    workspaces,
                    ssh_key=key,
                    network_url="https://example.test/pressure",
                    duration_seconds=10,
                    evidence_path=evidence,
                    runner=HealthRunner(),
                )
            recorded = json.loads(evidence.read_text())
            self.assertEqual(recorded["result"], "failed")
            self.assertEqual(len(recorded["cleanup_errors"]), 2)


if __name__ == "__main__":
    unittest.main()
