from dataclasses import dataclass
from typing import Protocol


class Reader(Protocol):
    def get(self, path: str) -> object: ...


class Client(Reader, Protocol):
    def post(self, path: str, payload: object) -> object: ...


def reconcile_interfaces(
    client: Reader,
    assignment_api_available: bool,
    desired_interfaces: list[object],
) -> None:
    if not assignment_api_available:
        raise RuntimeError("assignment API unavailable")
    client.get("/api/interfaces/assignment/search_item")


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
