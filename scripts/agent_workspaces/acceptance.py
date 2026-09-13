from __future__ import annotations

import concurrent.futures
import json
import os
import pathlib
import shlex
import subprocess
import time
import urllib.parse
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from .core import Workspace, WorkspaceError
from .lifecycle import deprovision_workspace, provision_status

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _run(
    runner: Runner,
    command: Sequence[str],
    *,
    timeout: float,
) -> tuple[str, float]:
    started = time.monotonic()
    result = runner(
        command,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    elapsed = time.monotonic() - started
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise WorkspaceError(f"command failed ({' '.join(command)}): {detail}")
    return result.stdout.strip(), elapsed


def _kubectl(command: Sequence[str]) -> list[str]:
    return ["k3s", "kubectl", *command]


def collect_host_health(runner: Runner = subprocess.run) -> dict[str, Any]:
    slice_raw, slice_seconds = _run(
        runner,
        [
            "systemctl",
            "show",
            "machine-agent\\x2dworkspaces.slice",
            "--property=CPUUsageNSec",
            "--property=MemoryCurrent",
            "--property=MemoryPeak",
            "--property=CPUQuotaPerSecUSec",
            "--property=MemoryHigh",
            "--property=MemoryMax",
            "--property=ManagedOOMMemoryPressure",
        ],
        timeout=10,
    )
    slice_values = dict(
        line.split("=", 1) for line in slice_raw.splitlines() if "=" in line
    )
    nodes_raw, nodes_seconds = _run(
        runner, _kubectl(["get", "nodes", "-o", "json"]), timeout=15
    )
    try:
        nodes = json.loads(nodes_raw)["items"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise WorkspaceError(f"invalid Kubernetes node response: {error}") from error
    ready_nodes = []
    etcd_voters = []
    pressure = []
    for node in nodes:
        conditions = {
            condition["type"]: condition["status"]
            for condition in node.get("status", {}).get("conditions", [])
        }
        name = node.get("metadata", {}).get("name", "unknown")
        if conditions.get("Ready") == "True":
            ready_nodes.append(name)
        if conditions.get("EtcdIsVoter") == "True":
            etcd_voters.append(name)
        for condition in ("MemoryPressure", "DiskPressure", "PIDPressure"):
            if conditions.get(condition) == "True":
                pressure.append(f"{name}:{condition}")
    if len(ready_nodes) != len(nodes) or not etcd_voters or pressure:
        raise WorkspaceError(
            "cluster health failed: "
            f"ready={len(ready_nodes)}/{len(nodes)}, etcd_voters={len(etcd_voters)}, "
            f"pressure={pressure}"
        )

    readyz, readyz_seconds = _run(
        runner, _kubectl(["get", "--raw=/readyz"]), timeout=15
    )
    if readyz != "ok":
        raise WorkspaceError(f"Kubernetes readyz failed: {readyz}")

    postgres, postgres_seconds = _run(
        runner,
        _kubectl(
            [
                "exec",
                "-n",
                "home-assistant",
                "deployment/home-assistant-postgres",
                "--",
                "sh",
                "-ec",
                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT 1"',
            ]
        ),
        timeout=15,
    )
    if postgres != "1":
        raise WorkspaceError(f"PostgreSQL query returned unexpected output: {postgres}")

    ha_code, ha_seconds = _run(
        runner,
        [
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--output",
            "/dev/null",
            "--write-out",
            "%{http_code}",
            "--max-time",
            "10",
            "http://10.0.40.13:8123/",
        ],
        timeout=15,
    )
    if ha_code != "200":
        raise WorkspaceError(f"Home Assistant returned HTTP {ha_code}")

    return {
        "captured_at": datetime.now(UTC).isoformat(),
        "nodes": {
            "ready": len(ready_nodes),
            "total": len(nodes),
            "seconds": nodes_seconds,
        },
        "etcd": {"voters": len(etcd_voters), "readyz_seconds": readyz_seconds},
        "postgres": {"query": "SELECT 1", "seconds": postgres_seconds},
        "home_assistant": {"http_status": 200, "seconds": ha_seconds},
        "pressure_conditions": pressure,
        "workspace_slice": {
            "cpu_usage_nsec": int(slice_values["CPUUsageNSec"]),
            "memory_current_bytes": int(slice_values["MemoryCurrent"]),
            "memory_peak_bytes": int(slice_values["MemoryPeak"]),
            "cpu_quota_per_second": slice_values["CPUQuotaPerSecUSec"],
            "memory_high_bytes": int(slice_values["MemoryHigh"]),
            "memory_max_bytes": int(slice_values["MemoryMax"]),
            "oomd_action": slice_values["ManagedOOMMemoryPressure"],
            "seconds": slice_seconds,
        },
    }


def _guest_ssh_command(
    workspace: Workspace, ssh_key: pathlib.Path, remote_command: str
) -> list[str]:
    address = workspace.raw["network"]["address"].split("/", 1)[0]
    return [
        "ssh",
        "-i",
        str(ssh_key),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "ConnectTimeout=5",
        f"{workspace.raw['guest_username']}@{address}",
        remote_command,
    ]


def _pressure_command(
    workspace: Workspace,
    peer: Workspace,
    *,
    duration_seconds: int,
    network_url: str,
) -> str:
    peer_address = peer.raw["network"]["address"].split("/", 1)[0]
    cpu_workers = workspace.raw["resources"]["vcpus"]
    return " ".join(
        [
            "set -eu;",
            "rx_before=$(cat /sys/class/net/workspace0/statistics/rx_bytes);",
            "tx_before=$(cat /sys/class/net/workspace0/statistics/tx_bytes);",
            "disk_started=$(date +%s%N);",
            f"for _ in $(seq 1 {cpu_workers}); do timeout {duration_seconds} yes >/dev/null & done;",
            "cpu_pids=$(jobs -p);",
            "sudo dd if=/dev/zero of=/dev/vdb bs=4M count=256 conv=fdatasync status=none &",
            "disk_pid=$!;",
            f"timeout {duration_seconds} sh -c {shlex.quote('while true; do curl --fail --silent --show-error --max-time 10 --output /dev/null ' + shlex.quote(network_url) + '; done')} &",
            "network_pid=$!;",
            f"python3 -c \"import socket; s=socket.socket(); s.settimeout(2); result=s.connect_ex(('{peer_address}',22)); raise SystemExit(0 if result != 0 else 1)\";",
            "wait $disk_pid;",
            "disk_finished=$(date +%s%N);",
            "wait $network_pid || test $? -eq 124;",
            "wait $cpu_pids || true;",
            "rx_after=$(cat /sys/class/net/workspace0/statistics/rx_bytes);",
            "tx_after=$(cat /sys/class/net/workspace0/statistics/tx_bytes);",
            'printf \'{"disk_bytes":1073741824,"disk_seconds":%s,"rx_bytes":%s,"tx_bytes":%s}\\n\' "$(( (disk_finished-disk_started)/1000000000 ))" "$((rx_after-rx_before))" "$((tx_after-tx_before))"',
        ]
    )


def run_two_guest_acceptance(
    workspaces: list[Workspace],
    *,
    ssh_key: pathlib.Path,
    network_url: str,
    duration_seconds: int,
    evidence_path: pathlib.Path,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    if len(workspaces) != 2 or any(
        not workspace.id.startswith("acceptance-") or not workspace.raw["enabled"]
        for workspace in workspaces
    ):
        raise WorkspaceError(
            "live acceptance requires exactly two enabled acceptance-* workspaces"
        )
    if os.geteuid() != 0:
        raise WorkspaceError("live acceptance must run as root on the workspace host")
    if duration_seconds < 10 or duration_seconds > 300:
        raise WorkspaceError("pressure duration must be between 10 and 300 seconds")
    parsed_url = urllib.parse.urlparse(network_url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise WorkspaceError("network pressure URL must be an absolute HTTPS URL")
    if not ssh_key.is_file() or ssh_key.is_symlink():
        raise WorkspaceError("SSH private key is missing or unsafe")
    for workspace in workspaces:
        status = provision_status(workspace, runner)
        if not status["consistent"] or status["domain_state"] != "running":
            raise WorkspaceError(
                f"workspace {workspace.id} is not consistently running"
            )

    evidence: dict[str, Any] = {
        "schema_version": 1,
        "kind": "agent-workspace-two-guest-acceptance",
        "workspace_ids": sorted(workspace.id for workspace in workspaces),
        "duration_seconds": duration_seconds,
        "network_target_host": parsed_url.hostname,
        "health": {"before": collect_host_health(runner)},
        "result": "failed",
    }
    try:
        commands = [
            _guest_ssh_command(
                workspace,
                ssh_key,
                _pressure_command(
                    workspace,
                    workspaces[1 - index],
                    duration_seconds=duration_seconds,
                    network_url=network_url,
                ),
            )
            for index, workspace in enumerate(workspaces)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(_run, runner, command, timeout=duration_seconds + 45)
                for command in commands
            ]
            evidence["health"]["during"] = []
            while not all(future.done() for future in futures):
                time.sleep(min(5, duration_seconds / 2))
                try:
                    evidence["health"]["during"].append(collect_host_health(runner))
                except WorkspaceError:
                    for workspace in workspaces:
                        runner(
                            _guest_ssh_command(
                                workspace,
                                ssh_key,
                                "sudo pkill -x yes || true; sudo pkill -x dd || true; sudo pkill -x curl || true",
                            ),
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=10,
                        )
                    raise
            pressure = [future.result() for future in futures]
        evidence["pressure"] = []
        for workspace, result in zip(workspaces, pressure, strict=True):
            try:
                metrics = json.loads(result[0])
            except json.JSONDecodeError as error:
                raise WorkspaceError(
                    f"workspace {workspace.id} returned invalid pressure metrics"
                ) from error
            evidence["pressure"].append(
                {"workspace_id": workspace.id, "seconds": result[1], **metrics}
            )
        evidence["health"]["after"] = collect_host_health(runner)
        evidence["result"] = "accepted"
    finally:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        for workspace in workspaces:
            try:
                deprovision_workspace(workspace, authorized=True, runner=runner)
            except WorkspaceError as error:
                evidence.setdefault("cleanup_errors", []).append(str(error))
        if evidence.get("cleanup_errors"):
            evidence["result"] = "failed"
        evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if evidence.get("cleanup_errors"):
        raise WorkspaceError("live acceptance cleanup failed; inspect evidence")
    return evidence
