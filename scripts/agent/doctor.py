from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_doctor(root: Path) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    for command in (
        "git",
        "just",
        "python",
        "node",
        "jq",
        "timeout",
        "nix",
        "nixfmt",
        "ruff",
        "pyright",
        "yamllint",
        "kubectl",
        "kubeconform",
        "tofu",
        "gitleaks",
        "shellcheck",
    ):
        found = shutil.which(command)
        checks.append(
            {
                "name": f"command:{command}",
                "status": "pass" if found else "fail",
                "detail": found or "not found",
                "remedy": "" if found else "run nix develop ./flake",
            }
        )
    for relative in (
        "flake/flake.nix",
        "scripts/agent",
        "scripts/checks",
        "tests",
        "gitops",
        "tofu/opnsense",
    ):
        present = (root / relative).exists()
        checks.append(
            {
                "name": f"path:{relative}",
                "status": "pass" if present else "fail",
                "detail": "present" if present else "missing",
                "remedy": ""
                if present
                else f"restore required repository path {relative}",
            }
        )
    for relative in (
        ".claude/settings.json",
        ".codex/config.toml",
        ".codex/hooks.json",
        ".cursor/hooks.json",
        ".mcp.json",
        ".opencode/plugins/agent-harness.js",
        "opencode.json",
    ):
        present = (root / relative).is_file()
        checks.append(
            {
                "name": f"adapter:{relative}",
                "status": "pass" if present else "unavailable",
                "detail": "configured" if present else "not configured",
                "remedy": "use explicit just agent-context and task-checkpoint commands"
                if not present
                else "",
            }
        )
    for relative in (
        "hooks/session-start",
        "hooks/stop",
        "hooks/validation-result",
    ):
        executable = (root / relative).is_file() and os.access(root / relative, os.X_OK)
        checks.append(
            {
                "name": f"hook:{relative}",
                "status": "pass" if executable else "fail",
                "detail": "executable" if executable else "missing or not executable",
                "remedy": ""
                if executable
                else f"restore executable {relative} from git",
            }
        )
    credential_refs = (root / ".gitlab-ci.yml").read_text(encoding="utf-8")
    for name in (
        "OPNSENSE_API_KEY",
        "OPNSENSE_API_SECRET",
        "OPNSENSE_CA_FILE",
        "SSH_DEPLOY_KEY",
        "HASS_TOKEN",
    ):
        present = name in credential_refs or any(
            name in path.read_text(encoding="utf-8")
            for path in (root / "opnsense_reconciler").glob("*.py")
        )
        checks.append(
            {
                "name": f"credential-reference:{name}",
                "status": "pass" if present else "unavailable",
                "detail": "reference present" if present else "reference absent",
                "remedy": "configure the protected CI variable reference"
                if not present
                else "",
            }
        )
    status = (
        "fail"
        if any(item["status"] == "fail" for item in checks)
        else (
            "unavailable"
            if any(item["status"] == "unavailable" for item in checks)
            else "pass"
        )
    )
    return {
        "schema_version": 1,
        "command": "doctor",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "checks": checks,
    }
