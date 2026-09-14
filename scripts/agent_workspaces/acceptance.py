from __future__ import annotations

import concurrent.futures
import json
import os
import pathlib
import re
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
MIN_CPU_SECONDS_PER_WALL_SECOND = 1.5
MIN_DISK_BYTES_PER_GUEST = 1024 * 1024 * 1024
MIN_NETWORK_RX_BYTES_PER_GUEST = 64 * 1024 * 1024
MIN_DURATION_RATIO = 0.9


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


def _verify_guest_listeners(
    workspaces: list[Workspace], ssh_key: pathlib.Path, runner: Runner
) -> None:
    for workspace in workspaces:
        output, _ = _run(
            runner,
            _guest_ssh_command(workspace, ssh_key, "ss -H -ltn 'sport = :22'"),
            timeout=10,
        )
        if "LISTEN" not in output:
            raise WorkspaceError(
                f"workspace {workspace.id} has no listening SSH target"
            )


def _probe_peer_denial(
    workspace: Workspace,
    peer: Workspace,
    ssh_key: pathlib.Path,
    runner: Runner,
) -> None:
    peer_address = peer.raw["network"]["address"].split("/", 1)[0]
    script = (
        "import socket; "
        "s=socket.socket(); s.settimeout(3); "
        f"target=('{peer_address}',22); "
        "\ntry: s.connect(target)"
        "\nexcept TimeoutError: print('timeout')"
        "\nexcept OSError as error: raise SystemExit(f'unexpected socket error: {error.errno}')"
        "\nelse: raise SystemExit('peer SSH connection succeeded')"
    )
    output, _ = _run(
        runner,
        _guest_ssh_command(workspace, ssh_key, f"python3 -c {shlex.quote(script)}"),
        timeout=10,
    )
    if output != "timeout":
        raise WorkspaceError(
            f"workspace {workspace.id} returned ambiguous peer denial: {output}"
        )


def _direction_drop_counter(
    workspace: Workspace, peer: Workspace, runner: Runner
) -> int:
    output, _ = _run(
        runner,
        ["nft", "-a", "list", "chain", "inet", "agent-workspaces", "forward"],
        timeout=10,
    )
    source_bridge = workspace.raw["network"]["bridge"]
    peer_bridge = peer.raw["network"]["bridge"]
    counts = [
        int(match.group(1))
        for line in output.splitlines()
        if (f'iifname "{source_bridge}"' in line or f'oifname "{peer_bridge}"' in line)
        and " drop" in line
        if (match := re.search(r"counter packets (\d+)", line)) is not None
    ]
    if not counts:
        raise WorkspaceError(
            f"workspace direction {workspace.id} to {peer.id} has no observable host firewall drop rule"
        )
    return sum(counts)


def _contain_workspaces(workspaces: list[Workspace], runner: Runner) -> list[str]:
    errors = []
    for workspace in workspaces:
        for command in (
            ["ip", "link", "set", "dev", workspace.raw["network"]["tap"], "down"],
            ["virsh", "destroy", workspace.domain_name],
        ):
            try:
                result = runner(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
            except (OSError, subprocess.SubprocessError) as error:
                errors.append(f"{' '.join(command)}: {error}")
                continue
            if result.returncode != 0:
                detail = result.stderr.strip() or result.stdout.strip()
                if (
                    "not found" not in detail.lower()
                    and "not running" not in detail.lower()
                ):
                    errors.append(f"{' '.join(command)}: {detail}")
    return errors


def _validate_measured_load(evidence: dict[str, Any]) -> None:
    duration = evidence["duration_seconds"]
    pressure = evidence.get("pressure", [])
    if len(pressure) != 2:
        raise WorkspaceError("pressure metrics are missing for one or more guests")
    for metrics in pressure:
        workspace_id = metrics["workspace_id"]
        if metrics["seconds"] < duration * MIN_DURATION_RATIO:
            raise WorkspaceError(f"workspace {workspace_id} pressure ended too early")
        if metrics["disk_bytes"] < MIN_DISK_BYTES_PER_GUEST:
            raise WorkspaceError(f"workspace {workspace_id} disk pressure was too low")
        if metrics["rx_bytes"] < MIN_NETWORK_RX_BYTES_PER_GUEST:
            raise WorkspaceError(
                f"workspace {workspace_id} network pressure was too low"
            )
    before_cpu = evidence["health"]["before"]["workspace_slice"]["cpu_usage_nsec"]
    after_cpu = evidence["health"]["after"]["workspace_slice"]["cpu_usage_nsec"]
    minimum_cpu = int(duration * MIN_CPU_SECONDS_PER_WALL_SECOND * 1_000_000_000)
    if after_cpu - before_cpu < minimum_cpu:
        raise WorkspaceError("aggregate workspace CPU pressure was too low")
    firewall = evidence["isolation"]["firewall_drop_delta"]
    if any(delta < 1 for delta in firewall.values()):
        raise WorkspaceError("host firewall did not record both isolation probes")


def _pressure_command(
    workspace: Workspace,
    *,
    duration_seconds: int,
    network_url: str,
) -> str:
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
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "kind": "agent-workspace-two-guest-acceptance",
        "workspace_ids": sorted(workspace.id for workspace in workspaces),
        "duration_seconds": duration_seconds,
        "network_target_host": parsed_url.hostname,
        "health": {},
        "result": "failed",
    }
    executor: concurrent.futures.ThreadPoolExecutor | None = None
    failure: Exception | None = None
    cleanup_errors: list[str] = []
    evidence_error: OSError | None = None
    try:
        try:
            for workspace in workspaces:
                status = provision_status(workspace, runner)
                if not status["consistent"] or status["domain_state"] != "running":
                    raise WorkspaceError(
                        f"workspace {workspace.id} is not consistently running"
                    )
            evidence["health"]["before"] = collect_host_health(runner)
            _verify_guest_listeners(workspaces, ssh_key, runner)
            firewall_delta = {}
            for index, workspace in enumerate(workspaces):
                peer = workspaces[1 - index]
                drop_before = _direction_drop_counter(workspace, peer, runner)
                _probe_peer_denial(workspace, peer, ssh_key, runner)
                drop_after = _direction_drop_counter(workspace, peer, runner)
                firewall_delta[workspace.id] = drop_after - drop_before
                if firewall_delta[workspace.id] < 1:
                    raise WorkspaceError(
                        f"host firewall did not record isolation probe from {workspace.id}"
                    )
            commands = [
                _guest_ssh_command(
                    workspace,
                    ssh_key,
                    _pressure_command(
                        workspace,
                        duration_seconds=duration_seconds,
                        network_url=network_url,
                    ),
                )
                for workspace in workspaces
            ]
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
            futures = [
                executor.submit(_run, runner, command, timeout=duration_seconds + 45)
                for command in commands
            ]
            evidence["health"]["during"] = []
            while not all(future.done() for future in futures):
                time.sleep(min(5, duration_seconds / 2))
                evidence["health"]["during"].append(collect_host_health(runner))
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
            evidence["isolation"] = {
                "listeners_verified": [workspace.id for workspace in workspaces],
                "firewall_drop_delta": firewall_delta,
            }
            evidence["health"]["after"] = collect_host_health(runner)
            _validate_measured_load(evidence)
            evidence["result"] = "accepted"
        except (WorkspaceError, OSError, subprocess.SubprocessError) as error:
            failure = error
            evidence["failure"] = {
                "type": type(error).__name__,
                "detail": str(error),
            }
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        cleanup_errors.extend(_contain_workspaces(workspaces, runner))
        for workspace in workspaces:
            try:
                deprovision_workspace(workspace, authorized=True, runner=runner)
            except (WorkspaceError, OSError, subprocess.SubprocessError) as error:
                cleanup_errors.append(str(error))
        if cleanup_errors:
            evidence["cleanup_errors"] = cleanup_errors
            evidence["result"] = "failed"
        try:
            evidence_path.parent.mkdir(parents=True, exist_ok=True)
            evidence_path.write_text(
                json.dumps(evidence, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            evidence_error = error
    if failure is not None:
        raise failure
    if cleanup_errors:
        raise WorkspaceError("live acceptance cleanup failed; inspect evidence")
    if evidence_error is not None:
        raise WorkspaceError(f"cannot write acceptance evidence: {evidence_error}")
    return evidence
