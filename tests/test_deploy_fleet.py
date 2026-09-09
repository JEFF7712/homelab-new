import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.deploy_fleet import (
    FLEET_HOSTS,
    FleetDeployer,
    FleetDeploymentError,
    FleetLock,
    LockContentionError,
    build_parser,
    main,
    parse_targets,
    verify_bgp_peer,
    verify_k3s_nodes_ready,
    verify_ssh,
)


class DeployFleetTest(unittest.TestCase):
    def test_parse_targets_default_order(self) -> None:
        targets = parse_targets(None)
        names = [t.name for t in targets]
        self.assertEqual(
            names,
            ["homelab-02", "homelab-03", "homelab-01", "adguard-netbird-01", "nas-01"],
        )

    def test_parse_targets_subset_preserves_canonical_order(self) -> None:
        targets = parse_targets(["nas-01", "homelab-01", "homelab-02"])
        names = [t.name for t in targets]
        self.assertEqual(names, ["homelab-02", "homelab-01", "nas-01"])

    def test_parse_targets_comma_separated(self) -> None:
        targets = parse_targets(["homelab-03,homelab-01"])
        names = [t.name for t in targets]
        self.assertEqual(names, ["homelab-03", "homelab-01"])

    def test_parse_targets_invalid_name(self) -> None:
        with self.assertRaises(FleetDeploymentError):
            parse_targets(["unknown-host"])

    def test_fleet_lock_acquire_and_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "deploy.lock"
            lock = FleetLock(lock_path, metadata={"test": True})
            with lock:
                self.assertTrue(lock_path.is_file())
                content = json.loads(lock_path.read_text())
                self.assertTrue(content["test"])
                self.assertIn("pid", content)
            self.assertFalse(lock_path.is_file())

    def test_fleet_lock_contention(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "deploy.lock"
            lock1 = FleetLock(lock_path)
            lock1.acquire()
            try:
                lock2 = FleetLock(lock_path)
                with self.assertRaises(LockContentionError):
                    lock2.acquire()
            finally:
                lock1.release()

    def test_verify_ssh_success(self) -> None:
        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 0, "", "")

        self.assertTrue(verify_ssh("10.0.30.12", "rupan", runner=runner))

    def test_verify_ssh_failure(self) -> None:
        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 255, "", "Connection refused")

        self.assertFalse(verify_ssh("10.0.30.12", "rupan", runner=runner))

    def test_verify_k3s_nodes_ready_all_ready(self) -> None:
        nodes_payload = {
            "items": [
                {
                    "metadata": {"name": "homelab-01"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
                {
                    "metadata": {"name": "homelab-02"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
                {
                    "metadata": {"name": "homelab-03"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
            ]
        }

        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 0, json.dumps(nodes_payload), "")

        ready, msg = verify_k3s_nodes_ready(runner=runner)
        self.assertTrue(ready)
        self.assertIn("All K3s nodes are Ready", msg)

    def test_verify_k3s_nodes_ready_one_not_ready(self) -> None:
        nodes_payload = {
            "items": [
                {
                    "metadata": {"name": "homelab-01"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
                {
                    "metadata": {"name": "homelab-02"},
                    "status": {"conditions": [{"type": "Ready", "status": "False"}]},
                },
                {
                    "metadata": {"name": "homelab-03"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
            ]
        }

        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 0, json.dumps(nodes_payload), "")

        ready, msg = verify_k3s_nodes_ready(runner=runner)
        self.assertFalse(ready)
        self.assertIn("Node homelab-02 is NotReady", msg)

    def test_verify_k3s_nodes_ready_missing_node(self) -> None:
        nodes_payload = {
            "items": [
                {
                    "metadata": {"name": "homelab-01"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
                {
                    "metadata": {"name": "homelab-02"},
                    "status": {"conditions": [{"type": "Ready", "status": "True"}]},
                },
            ]
        }

        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 0, json.dumps(nodes_payload), "")

        ready, msg = verify_k3s_nodes_ready(runner=runner)
        self.assertFalse(ready)
        self.assertIn("Cluster missing expected nodes: homelab-03", msg)

    def test_verify_bgp_peer_success(self) -> None:
        def runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            if "get" in argv and "pods" in argv:
                return subprocess.CompletedProcess(argv, 0, "cilium-dgfw4\n", "")
            if "cilium-dbg" in argv:
                return subprocess.CompletedProcess(
                    argv,
                    0,
                    "Session State: established\nPeer: 10.0.30.1\n",
                    "",
                )
            return subprocess.CompletedProcess(argv, 0, "", "")

        ok, msg = verify_bgp_peer(runner=runner)
        self.assertTrue(ok)
        self.assertIn("established", msg)

    def test_deployer_k3s_worker_sequence(self) -> None:
        executed_commands: list[list[str]] = []

        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            executed_commands.append(argv)
            if "node" in argv and "get" in argv:
                return subprocess.CompletedProcess(argv, 0, "True", "")
            return subprocess.CompletedProcess(argv, 0, "", "")

        sleeps: list[float] = []

        deployer = FleetDeployer(
            targets=[FLEET_HOSTS["homelab-02"]],
            skip_preflight=True,
            cooldown_seconds=10.0,
            runner=mock_runner,
            sleeper=sleeps.append,
        )

        result = deployer.execute()
        self.assertEqual(result["status"], "success")

        # Verify command sequence: cordon -> drain -> rebuild switch -> wait node ready -> uncordon
        cmd_verbs = [" ".join(c[:2]) for c in executed_commands]
        self.assertIn("kubectl cordon", cmd_verbs)
        self.assertIn("kubectl drain", cmd_verbs)
        self.assertIn("nixos-rebuild switch", cmd_verbs)
        self.assertIn("kubectl uncordon", cmd_verbs)
        self.assertEqual(sleeps, [10.0])

    def test_deployer_stateful_anchor_verifies_postgres(self) -> None:
        executed_commands: list[list[str]] = []

        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            executed_commands.append(argv)
            if "node" in argv and "get" in argv:
                return subprocess.CompletedProcess(argv, 0, "True", "")
            if "get" in argv and "pods" in argv:
                return subprocess.CompletedProcess(argv, 0, "cilium-dgfw4\n", "")
            if "cilium-dbg" in argv:
                return subprocess.CompletedProcess(
                    argv, 0, "Session State: established\n", ""
                )
            return subprocess.CompletedProcess(argv, 0, "", "")

        deployer = FleetDeployer(
            targets=[FLEET_HOSTS["homelab-01"]],
            skip_preflight=True,
            skip_cooldown=True,
            runner=mock_runner,
        )

        result = deployer.execute()
        self.assertEqual(result["status"], "success")

        rollout_cmds = [
            " ".join(c) for c in executed_commands if "rollout" in c and "status" in c
        ]
        self.assertEqual(len(rollout_cmds), 2)
        self.assertTrue(any("home-assistant-postgres" in cmd for cmd in rollout_cmds))
        self.assertTrue(any("immich-postgres" in cmd for cmd in rollout_cmds))

    def test_deployer_appliances(self) -> None:
        executed_commands: list[list[str]] = []

        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            executed_commands.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        checked_sockets: list[tuple[str, int]] = []
        checked_urls: list[str] = []

        def mock_socket(host: str, port: int, timeout: float) -> bool:
            del timeout
            checked_sockets.append((host, port))
            return True

        def mock_http(url: str, timeout: float) -> bool:
            del timeout
            checked_urls.append(url)
            return True

        deployer = FleetDeployer(
            targets=[FLEET_HOSTS["adguard-netbird-01"], FLEET_HOSTS["nas-01"]],
            skip_preflight=True,
            skip_cooldown=True,
            runner=mock_runner,
            socket_checker=mock_socket,
            http_checker=mock_http,
        )

        result = deployer.execute()
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["hosts"]), 2)

        # NAS appliance should check port 2049 and Attic URL
        self.assertIn(("10.0.30.20", 2049), checked_sockets)
        self.assertIn("http://10.0.30.20:8080/", checked_urls)

    def test_circuit_breaker_halts_on_failure_and_uncordons(self) -> None:
        executed_commands: list[list[str]] = []

        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            executed_commands.append(argv)
            # Fail rebuild on homelab-02
            if "nixos-rebuild" in argv:
                return subprocess.CompletedProcess(
                    argv, 1, "", "nixos-rebuild switch failed"
                )
            return subprocess.CompletedProcess(argv, 0, "", "")

        deployer = FleetDeployer(
            targets=[FLEET_HOSTS["homelab-02"], FLEET_HOSTS["homelab-03"]],
            skip_preflight=True,
            skip_cooldown=True,
            runner=mock_runner,
        )

        with self.assertRaises(FleetDeploymentError):
            deployer.execute()

        # Check that homelab-03 was NEVER touched
        hosts_targeted = [
            c[c.index("--flake") + 1] for c in executed_commands if "--flake" in c
        ]
        self.assertEqual(hosts_targeted, ["./flake#homelab-02"])

        # Check that uncordon was attempted during recovery of homelab-02
        uncordon_cmds = [
            c
            for c in executed_commands
            if len(c) >= 3 and c[0] == "kubectl" and c[1] == "uncordon"
        ]
        self.assertTrue(len(uncordon_cmds) >= 1)
        self.assertEqual(uncordon_cmds[-1][2], "homelab-02")

    def test_dry_run_flags(self) -> None:
        executed_commands: list[list[str]] = []

        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            executed_commands.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        deployer = FleetDeployer(
            targets=[FLEET_HOSTS["homelab-02"]],
            dry_run=True,
            skip_preflight=True,
            runner=mock_runner,
        )

        result = deployer.execute()
        self.assertTrue(result["dry_run"])

        # In dry run mode, cordon and drain should have --dry-run=client
        # and nixos-rebuild should be dry-activate
        for cmd in executed_commands:
            if cmd[0] == "kubectl" and cmd[1] in ("cordon", "drain"):
                self.assertIn("--dry-run=client", cmd)
            if cmd[0] == "nixos-rebuild":
                self.assertEqual(cmd[1], "dry-activate")

    def test_cli_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--target",
                "homelab-02",
                "--dry-run",
                "--skip-preflight",
                "--cooldown-seconds",
                "15",
            ]
        )
        self.assertEqual(args.targets, ["homelab-02"])
        self.assertTrue(args.dry_run)
        self.assertTrue(args.skip_preflight)
        self.assertEqual(args.cooldown_seconds, 15.0)

    def test_main_cli_execution_success(self) -> None:
        def mock_runner(
            argv: list[str], **kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            del kwargs
            return subprocess.CompletedProcess(argv, 0, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = str(Path(tmpdir) / "test.lock")
            ret = main(
                [
                    "--target",
                    "homelab-02",
                    "--dry-run",
                    "--skip-preflight",
                    "--lock-file",
                    lock_path,
                ],
                runner=mock_runner,
            )
            self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
