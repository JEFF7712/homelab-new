import argparse
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

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
    if not resolved_interfaces:
        return
    existing_devices = _assignment_devices(assignments)
    additions = [
        desired
        for desired in resolved_interfaces
        if desired["if"] not in existing_devices
    ]
    for desired in additions:
        client.post("/api/interfaces/assignment/add_item", {"interface": desired})
    if additions:
        client.post("/api/interfaces/assignment/reconfigure", {})
    runtime = _runtime_interfaces(
        client.get("/api/interfaces/overview/interfaces_info/true")
    )
    mismatches = [
        desired
        for desired in resolved_interfaces
        if runtime.get(desired["if"]) != (desired.get("ipaddr"), desired.get("descr"))
    ]
    if mismatches:
        devices = ", ".join(str(desired["if"]) for desired in mismatches)
        raise RuntimeError(
            "interface runtime drift for "
            f"{devices}; OPNsense 26.7 assignment API cannot configure static L3 fields"
        )


def reconcile_kea_interfaces(client: Client, desired_interfaces: set[str]) -> None:
    current = client.get("/api/kea/dhcpv4/get")
    if _kea_interfaces(current) != desired_interfaces:
        client.post(
            "/api/kea/dhcpv4/set",
            {
                "dhcpv4": {
                    "general": {
                        "enabled": "1",
                        "manual_config": "0",
                        "interfaces": ",".join(sorted(desired_interfaces)),
                        "valid_lifetime": "4000",
                        "fwrules": "1",
                        "dhcp_socket_type": "raw",
                    }
                }
            },
        )
        client.post("/api/kea/service/reconfigure", {})
    verified = client.get("/api/kea/dhcpv4/get")
    if _kea_interfaces(verified) != desired_interfaces:
        raise RuntimeError("Kea DHCPv4 interface verification failed")
    status = client.get("/api/kea/service/status")
    if not isinstance(status, dict) or status.get("status") != "running":
        raise RuntimeError("Kea DHCPv4 service is not running")


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
        assignment = {
            key: value for key, value in desired.items() if key not in {"parent", "tag"}
        }
        assignment["if"] = device
        resolved.append(assignment)
    return resolved


@dataclass(frozen=True)
class BgpProof:
    missing_peers: set[str]
    missing_routes: set[str]
    ready: bool
    service_running: bool


BGP_NEIGHBOR_FIELDS = (
    "address",
    "description",
    "remoteas",
    "updatesource",
    "nexthopself",
    "enabled",
)


def reconcile_bgp_neighbors(
    client: Client,
    desired_neighbors: list[dict[str, object]],
) -> dict[str, int]:
    desired_by_address = _desired_bgp_neighbors(desired_neighbors)
    live_by_address = _live_bgp_neighbors(client.get("/api/quagga/bgp/search_neighbor"))
    unexpected = sorted(set(live_by_address) - set(desired_by_address))
    if unexpected:
        raise RuntimeError(
            "unexpected BGP neighbors require human-directed removal: "
            + ", ".join(unexpected)
        )
    changed = False
    for address, desired in desired_by_address.items():
        live = live_by_address.get(address)
        if live is None:
            _require_stored(
                client.post("/api/quagga/bgp/add_neighbor", {"neighbor": desired})
            )
            changed = True
        elif {key: live.get(key) for key in BGP_NEIGHBOR_FIELDS} != desired:
            _require_stored(
                client.post(
                    f"/api/quagga/bgp/set_neighbor/{live['uuid']}",
                    {"neighbor": desired},
                )
            )
            changed = True
    if changed:
        client.post("/api/quagga/service/reconfigure", {})
    verified = _live_bgp_neighbors(client.get("/api/quagga/bgp/search_neighbor"))
    mismatches = sorted(
        address
        for address, desired in desired_by_address.items()
        if {key: verified.get(address, {}).get(key) for key in BGP_NEIGHBOR_FIELDS}
        != desired
    )
    if mismatches:
        raise RuntimeError(
            "BGP neighbor verification failed for " + ", ".join(mismatches)
        )
    return {
        address: int(str(desired["remoteas"]))
        for address, desired in desired_by_address.items()
    }


def _desired_bgp_neighbors(
    desired_neighbors: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    desired_by_address: dict[str, dict[str, object]] = {}
    for desired in desired_neighbors:
        if not isinstance(desired, dict):
            raise ValueError("BGP neighbors must contain objects")
        neighbor = {key: desired.get(key) for key in BGP_NEIGHBOR_FIELDS}
        address, remoteas, enabled = (
            neighbor["address"],
            neighbor["remoteas"],
            neighbor["enabled"],
        )
        if not isinstance(address, str) or not address:
            raise ValueError("BGP neighbor requires an address")
        if address in desired_by_address:
            raise ValueError(f"duplicate BGP neighbor address: {address}")
        if (
            not isinstance(remoteas, str)
            or not remoteas.isdigit()
            or not all(
                isinstance(neighbor[key], str) and neighbor[key]
                for key in BGP_NEIGHBOR_FIELDS
            )
            or enabled not in ("0", "1")
        ):
            raise ValueError(f"BGP neighbor {address} has invalid managed fields")
        desired_by_address[address] = neighbor
    if not desired_by_address:
        raise ValueError("BGP neighbors must not be empty")
    return desired_by_address


def _live_bgp_neighbors(response: object) -> dict[str, dict[str, object]]:
    rows = response.get("rows") if isinstance(response, dict) else None
    if not isinstance(rows, list):
        raise ValueError("BGP neighbor search response contains no rows")
    live_by_address: dict[str, dict[str, object]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        address, uuid = row.get("address"), row.get("uuid")
        if (
            not isinstance(address, str)
            or not address
            or not isinstance(uuid, str)
            or not uuid
        ):
            continue
        entry: dict[str, object] = {key: row.get(key) for key in BGP_NEIGHBOR_FIELDS}
        entry["uuid"] = uuid
        live_by_address[address] = entry
    return live_by_address


def _require_stored(response: object) -> None:
    if (
        not isinstance(response, dict)
        or response.get("result") == "failed"
        or "validations" in response
    ):
        raise RuntimeError(f"BGP neighbor store failed: {response}")


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
    unicast = response.get("ipv4Unicast")
    if isinstance(unicast, dict) and isinstance(unicast.get("peers"), dict):
        return unicast["peers"]
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
        prefix if "/" in prefix else f"{prefix}/32"
        for row in rows
        if isinstance(row, dict)
        for prefix in [row.get("prefix")]
        if isinstance(prefix, str) and prefix
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


def _runtime_interfaces(interfaces: object) -> dict[object, tuple[object, object]]:
    rows = interfaces.get("rows") if isinstance(interfaces, dict) else None
    if not isinstance(rows, list):
        return {}
    return {
        row.get("device"): (row.get("addr4"), row.get("description"))
        for row in rows
        if isinstance(row, dict) and row.get("device")
    }


def _kea_interfaces(configuration: object) -> set[str]:
    if not isinstance(configuration, dict):
        return set()
    dhcpv4 = configuration.get("dhcpv4")
    general = dhcpv4.get("general") if isinstance(dhcpv4, dict) else None
    interfaces = general.get("interfaces") if isinstance(general, dict) else None
    if not isinstance(interfaces, dict):
        return set()
    return {
        name
        for name, value in interfaces.items()
        if isinstance(name, str)
        and isinstance(value, dict)
        and value.get("selected") in (1, "1", True)
    }


def main(
    argv: list[str] | None = None,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[[str, Credentials, str, str | None], Client] = HttpsClient,
    reconcile: Callable[
        [Client, bool, list[dict[str, object]]], None
    ] = reconcile_interfaces,
    reconcile_kea: Callable[[Client, set[str]], None] = reconcile_kea_interfaces,
    reconcile_bgp: Callable[
        [Client, list[dict[str, object]]], dict[str, int]
    ] = reconcile_bgp_neighbors,
    prove_bgp: Callable[[Reader, dict[str, int], set[str]], BgpProof] = verify_bgp,
) -> None:
    parser = argparse.ArgumentParser(
        description="Reconcile OPNsense interface assignments"
    )
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--kea-interfaces", required=True, type=Path)
    parser.add_argument("--bgp-neighbors", required=True, type=Path)
    parser.add_argument("--bgp-expected-routes", required=True, type=Path)
    arguments = parser.parse_args(argv)
    environment = environ if environ is not None else os.environ
    required = (
        "OPNSENSE_URL",
        "OPNSENSE_API_KEY",
        "OPNSENSE_API_SECRET",
        "OPNSENSE_CA_FILE",
    )
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise ValueError(
            f"missing required environment variables: {', '.join(missing)}"
        )
    inventory = json.loads(arguments.inventory.read_text())
    desired = json.loads(arguments.assignments.read_text())
    desired_kea_interfaces = json.loads(arguments.kea_interfaces.read_text())
    desired_bgp_neighbors = json.loads(arguments.bgp_neighbors.read_text())
    expected_routes = json.loads(arguments.bgp_expected_routes.read_text())
    if not isinstance(inventory, dict) or not isinstance(
        inventory.get("assignment_api_available"), bool
    ):
        raise ValueError("inventory must contain assignment_api_available")
    if not isinstance(desired, list) or not all(
        isinstance(item, dict) for item in desired
    ):
        raise ValueError("assignments must contain a list of objects")
    if not isinstance(desired_kea_interfaces, list) or not all(
        isinstance(item, str) and item for item in desired_kea_interfaces
    ):
        raise ValueError("Kea interfaces must contain a list of interface identifiers")
    if not isinstance(desired_bgp_neighbors, list) or not all(
        isinstance(item, dict) for item in desired_bgp_neighbors
    ):
        raise ValueError("BGP neighbors must contain a list of objects")
    if not isinstance(expected_routes, list) or not all(
        isinstance(item, str) and item for item in expected_routes
    ):
        raise ValueError("BGP expected routes must contain a list of prefixes")
    client = client_factory(
        environment["OPNSENSE_URL"],
        Credentials(
            environment["OPNSENSE_API_KEY"], environment["OPNSENSE_API_SECRET"]
        ),
        environment["OPNSENSE_CA_FILE"],
        environment.get("OPNSENSE_TLS_SERVER_NAME"),
    )
    reconcile(client, inventory["assignment_api_available"], desired)
    reconcile_kea(client, set(desired_kea_interfaces))
    expected_peers = reconcile_bgp(client, desired_bgp_neighbors)
    proof = prove_bgp(client, expected_peers, set(expected_routes))
    if not proof.ready:
        raise RuntimeError(
            "BGP proof failed; missing peers: "
            + ", ".join(sorted(proof.missing_peers) or ["none"])
            + "; missing routes: "
            + ", ".join(sorted(proof.missing_routes) or ["none"])
        )
    print(
        json.dumps(
            {
                "assignment_count": len(desired),
                "bgp_peer_count": len(expected_peers),
                "kea_interface_count": len(desired_kea_interfaces),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
