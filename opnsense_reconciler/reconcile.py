import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Callable, Mapping, Protocol

from opnsense_reconciler.inventory import Credentials, HttpsClient


class Reader(Protocol):
    def get(self, path: str) -> object: ...


class Client(Reader, Protocol):
    def post(self, path: str, payload: object) -> object: ...


def reconcile_interfaces(
    client: Client,
    assignment_api_available: bool,
    desired_interfaces: list[dict[str, object]],
) -> None:
    if not assignment_api_available:
        raise RuntimeError("assignment API unavailable")
    resolved_interfaces = (
        resolve_vlan_devices(
            desired_interfaces,
            client.get("/api/interfaces/vlan_settings/search_item"),
        )
        if desired_interfaces
        else []
    )
    assignments = client.get("/api/interfaces/assignment/search_item")
    existing_devices = _assignment_devices(assignments)
    additions = [desired for desired in resolved_interfaces if desired["if"] not in existing_devices]
    for desired in additions:
        client.post("/api/interfaces/assignment/add_item", {"interface": desired})
    if additions:
        client.post("/api/interfaces/assignment/reconfigure", {})


def resolve_vlan_devices(
    desired_interfaces: list[dict[str, object]],
    live_vlans: object,
) -> list[dict[str, object]]:
    rows = live_vlans.get("rows") if isinstance(live_vlans, dict) else None
    if not isinstance(rows, list):
        rows = []
    live_devices = {
        (parent, tag): device.split(" ", maxsplit=1)[0]
        for row in rows
        if isinstance(row, dict)
        for parent in [row.get("if")]
        for raw_tag in [row.get("tag")]
        for device in [row.get("vlanif")]
        if isinstance(parent, str)
        and isinstance(raw_tag, (str, int))
        and str(raw_tag).isdigit()
        and isinstance(device, str)
        and device
        for tag in [int(raw_tag)]
    }
    resolved: list[dict[str, object]] = []
    for desired in desired_interfaces:
        parent = desired.get("parent")
        tag = desired.get("tag")
        if not isinstance(parent, str) or not isinstance(tag, int):
            raise ValueError("desired VLAN assignment requires parent and integer tag")
        device = live_devices.get((parent, tag))
        if device is None:
            raise RuntimeError(f"VLAN device unavailable for {parent} tag {tag}")
        assignment = {key: value for key, value in desired.items() if key not in {"parent", "tag"}}
        assignment["if"] = device
        resolved.append(assignment)
    return resolved


@dataclass(frozen=True)
class BgpProof:
    missing_peers: set[str]
    missing_routes: set[str]
    ready: bool
    service_running: bool


def verify_bgp(
    client: Reader,
    expected_peers: dict[str, int],
    expected_routes: set[str],
) -> BgpProof:
    status = client.get("/api/quagga/service/status")
    summary = client.get("/api/quagga/diagnostics/bgpsummary")
    routes = client.get("/api/quagga/diagnostics/search_bgproute4")
    service_running = isinstance(status, dict) and status.get("status") == "running"
    peers = _peers(summary)
    missing_peers = {
        address
        for address, asn in expected_peers.items()
        if not _peer_established(peers.get(address), asn)
    }
    available_routes = _route_prefixes(routes)
    missing_routes = expected_routes - available_routes
    return BgpProof(
        missing_peers=missing_peers,
        missing_routes=missing_routes,
        ready=service_running and not missing_peers and not missing_routes,
        service_running=service_running,
    )


def _peers(summary: object) -> dict[str, object]:
    if not isinstance(summary, dict):
        return {}
    response = summary.get("response")
    if not isinstance(response, dict):
        return {}
    peers = response.get("peers")
    return peers if isinstance(peers, dict) else {}


def _peer_established(peer: object, expected_asn: int) -> bool:
    if not isinstance(peer, dict):
        return False
    return peer.get("state") == "Established" and peer.get("remoteAs") == expected_asn


def _route_prefixes(routes: object) -> set[str]:
    if not isinstance(routes, dict):
        return set()
    rows = routes.get("rows")
    if not isinstance(rows, list):
        return set()
    return {
        prefix
        for row in rows
        if isinstance(row, dict)
        for prefix in [row.get("prefix")]
        if isinstance(prefix, str)
    }


def _assignment_devices(assignments: object) -> set[str]:
    if not isinstance(assignments, dict):
        return set()
    rows = assignments.get("rows")
    if not isinstance(rows, list):
        return set()
    return {
        device
        for row in rows
        if isinstance(row, dict)
        for device in [row.get("if")]
        if isinstance(device, str) and device
    }


def main(
    argv: list[str] | None = None,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[[str, Credentials, str, str | None], Client] = HttpsClient,
    reconcile: Callable[[Client, bool, list[dict[str, object]]], None] = reconcile_interfaces,
) -> None:
    parser = argparse.ArgumentParser(description="Reconcile OPNsense interface assignments")
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    arguments = parser.parse_args(argv)
    environment = environ if environ is not None else os.environ
    required = ("OPNSENSE_URL", "OPNSENSE_API_KEY", "OPNSENSE_API_SECRET", "OPNSENSE_CA_FILE")
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise ValueError(f"missing required environment variables: {', '.join(missing)}")
    inventory = json.loads(arguments.inventory.read_text())
    desired = json.loads(arguments.assignments.read_text())
    if not isinstance(inventory, dict) or not isinstance(inventory.get("assignment_api_available"), bool):
        raise ValueError("inventory must contain assignment_api_available")
    if not isinstance(desired, list) or not all(isinstance(item, dict) for item in desired):
        raise ValueError("assignments must contain a list of objects")
    client = client_factory(
        environment["OPNSENSE_URL"],
        Credentials(environment["OPNSENSE_API_KEY"], environment["OPNSENSE_API_SECRET"]),
        environment["OPNSENSE_CA_FILE"],
        environment.get("OPNSENSE_TLS_SERVER_NAME"),
    )
    reconcile(client, inventory["assignment_api_available"], desired)
    print(json.dumps({"assignment_count": len(desired)}, sort_keys=True))


if __name__ == "__main__":
    main()
