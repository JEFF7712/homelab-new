from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .acceptance import run_real_access_acceptance, run_two_guest_acceptance
from .core import WorkspaceError, load_manifest, render_plan
from .lifecycle import deprovision_workspace, provision_status, provision_workspace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.agent_workspaces")
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=pathlib.Path("config/agent-workspaces/workspaces.json"),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate the offline workspace inventory")
    subparsers.add_parser(
        "plan", help="render a deterministic, non-mutating libvirt plan"
    )
    status = subparsers.add_parser(
        "status", help="inspect domains, disks, and provisioning receipts"
    )
    status.add_argument("workspace_id")
    provision = subparsers.add_parser(
        "provision", help="provision one validated workspace"
    )
    provision.add_argument("workspace_id")
    provision.add_argument("--authorized", action="store_true")
    deprovision = subparsers.add_parser(
        "deprovision", help="undefine one verified workspace while preserving disks"
    )
    deprovision.add_argument("workspace_id")
    deprovision.add_argument("--authorized", action="store_true")
    acceptance = subparsers.add_parser(
        "acceptance-two-guest",
        help="run bounded pressure and health checks on two disposable guests",
    )
    acceptance.add_argument("--authorized", action="store_true")
    acceptance.add_argument("--ssh-key", required=True, type=pathlib.Path)
    acceptance.add_argument("--network-url", required=True)
    acceptance.add_argument("--duration", type=int, default=60)
    acceptance.add_argument("--evidence", required=True, type=pathlib.Path)

    real_access = subparsers.add_parser(
        "acceptance-real-access",
        help="run real access and cross-user isolation acceptance on two workspaces",
    )
    real_access.add_argument("--authorized", action="store_true")
    real_access.add_argument("--ssh-key", required=True, type=pathlib.Path)
    real_access.add_argument("--network-url", default="https://1.1.1.1")
    real_access.add_argument("--evidence", required=True, type=pathlib.Path)
    real_access.add_argument("--cleanup", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        workspaces = load_manifest(args.manifest)
        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "workspaces": len(workspaces),
                        "enabled": sum(item.raw["enabled"] for item in workspaces),
                    },
                    sort_keys=True,
                )
            )
        elif args.command == "plan":
            print(json.dumps(render_plan(workspaces), indent=2, sort_keys=True))
        elif args.command == "acceptance-two-guest":
            if not args.authorized:
                raise WorkspaceError(
                    "live acceptance requires the explicit --authorized flag"
                )
            result = run_two_guest_acceptance(
                workspaces,
                ssh_key=args.ssh_key,
                network_url=args.network_url,
                duration_seconds=args.duration,
                evidence_path=args.evidence,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
        elif args.command == "acceptance-real-access":
            if not args.authorized:
                raise WorkspaceError(
                    "live acceptance requires the explicit --authorized flag"
                )
            result = run_real_access_acceptance(
                workspaces,
                primary_ssh_key=args.ssh_key,
                network_url=args.network_url,
                evidence_path=args.evidence,
                cleanup=args.cleanup,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            selected = next(
                (
                    workspace
                    for workspace in workspaces
                    if workspace.id == args.workspace_id
                ),
                None,
            )
            if selected is None:
                raise WorkspaceError(f"unknown workspace: {args.workspace_id}")
            if args.command == "status":
                result = provision_status(selected)
            elif args.command == "provision":
                result = provision_workspace(selected, authorized=args.authorized)
            else:
                result = deprovision_workspace(selected, authorized=args.authorized)
            print(json.dumps(result, indent=2, sort_keys=True))
    except WorkspaceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
