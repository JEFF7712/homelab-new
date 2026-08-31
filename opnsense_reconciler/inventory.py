from dataclasses import dataclass
from typing import Protocol


class Client(Protocol):
    def get(self, path: str) -> object: ...


@dataclass(frozen=True)
class Credentials:
    key: str
    secret: str


@dataclass(frozen=True)
class Inventory:
    assignment_api_available: bool
    assignments: object | None
    backup: str
    backup_id: str
    backup_provider: str
    interfaces: object
    vlans: object


def collect_inventory(client: Client) -> Inventory:
    providers = client.get("/api/core/backup/providers")
    backup_provider = _first_identifier(providers)
    backups = client.get(f"/api/core/backup/backups/{backup_provider}")
    backup_id = _first_identifier(backups)
    backup = client.get(f"/api/core/backup/download/{backup_provider}/{backup_id}")
    interfaces = client.get("/api/interfaces/overview/interfaces_info/true")
    vlans = client.get("/api/interfaces/vlan_settings/search_item")
    assignments = client.get("/api/interfaces/assignment/search_item")
    return Inventory(
        assignment_api_available=True,
        assignments=assignments,
        backup=backup if isinstance(backup, str) else str(backup),
        backup_id=backup_id,
        backup_provider=backup_provider,
        interfaces=interfaces,
        vlans=vlans,
    )


def parse_credentials(contents: str) -> Credentials:
    values: dict[str, str] = {}
    for line in contents.splitlines():
        label, separator, value = line.partition(":")
        if separator and label.strip() in {"key", "secret"}:
            values[label.strip()] = value.strip()
    if not values.get("key") or not values.get("secret"):
        raise ValueError("credential file must contain key and secret labels")
    return Credentials(key=values["key"], secret=values["secret"])


def _first_identifier(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("OPNsense response is not an object")
    rows = response.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("OPNsense response contains no rows")
    first = rows[0]
    if not isinstance(first, dict):
        raise ValueError("OPNsense response row is not an object")
    identifier = first.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("OPNsense response row has no id")
    return identifier
