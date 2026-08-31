import argparse
from dataclasses import dataclass
import hashlib
import json
import os
import ssl
import socket
import subprocess
from pathlib import Path
from typing import Callable, Mapping, Protocol
from http.client import HTTPSConnection


class Client(Protocol):
    def get(self, path: str) -> object: ...

    def get_bytes(self, path: str) -> bytes: ...


@dataclass(frozen=True)
class Credentials:
    key: str
    secret: str


class HttpsClient:
    def __init__(self, base_url: str, credentials: Credentials, ca_file: str, server_name: str | None = None) -> None:
        self._host = base_url.removeprefix("https://").rstrip("/")
        self._server_name = server_name or self._host
        self._credentials = credentials
        self._context = ssl.create_default_context(cafile=ca_file)

    def get(self, path: str) -> object:
        return json.loads(self.get_bytes(path).decode())

    def get_bytes(self, path: str) -> bytes:
        if not path.startswith("/api/"):
            raise ValueError("API path must start with /api/")
        password = self._credentials.secret
        import base64
        token = base64.b64encode(f"{self._credentials.key}:{password}".encode()).decode()
        connection = _VerifiedConnection(self._host, self._server_name, self._context)
        try:
            connection.request("GET", path, headers={"Accept": "application/json", "Authorization": f"Basic {token}"})
            response = connection.getresponse()
            body = response.read()
            if response.status >= 400:
                raise RuntimeError(f"OPNsense returned HTTP {response.status}")
            return body
        finally:
            connection.close()


class _VerifiedConnection(HTTPSConnection):
    def __init__(self, host: str, server_name: str, context: ssl.SSLContext) -> None:
        super().__init__(host, context=context)
        self._server_name = server_name

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), self.timeout, self.source_address)
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self._server_name)


@dataclass(frozen=True)
class Inventory:
    assignment_api_available: bool
    assignments: object | None
    backup: bytes
    backup_id: str
    backup_provider: str
    interfaces: object
    vlans: object


def collect_inventory(client: Client) -> Inventory:
    providers = client.get("/api/core/backup/providers")
    backup_provider = _first_identifier(providers)
    backups = client.get(f"/api/core/backup/backups/{backup_provider}")
    backup_id = _first_identifier(backups)
    backup = client.get_bytes(f"/api/core/backup/download/{backup_provider}/{backup_id}")
    interfaces = client.get("/api/interfaces/overview/interfaces_info/true")
    vlans = client.get("/api/interfaces/vlan_settings/search_item")
    try:
        assignments = client.get("/api/interfaces/assignment/search_item")
    except RuntimeError as error:
        if not str(error).endswith(("HTTP 403", "HTTP 404")):
            raise
        assignments = None
    return Inventory(
        assignment_api_available=assignments is not None,
        assignments=assignments,
        backup=backup,
        backup_id=backup_id,
        backup_provider=backup_provider,
        interfaces=interfaces,
        vlans=vlans,
    )


def write_inventory_artifacts(
    inventory: Inventory,
    artifact_dir: Path,
    recipient: str,
    encrypt: Callable[[bytes, str, Path], None] | None = None,
) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    destination = artifact_dir / "config.xml.age"
    (encrypt or _encrypt_with_age)(inventory.backup, recipient, destination)
    summary = {
        "assignment_api_available": inventory.assignment_api_available,
        "backup_id": inventory.backup_id,
        "backup_provider": inventory.backup_provider,
        "backup_sha256": hashlib.sha256(inventory.backup).hexdigest(),
        "interfaces": inventory.interfaces,
        "vlans": inventory.vlans,
    }
    (artifact_dir / "inventory.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


def _encrypt_with_age(backup: bytes, recipient: str, destination: Path) -> None:
    subprocess.run(
        ["age", "--recipient", recipient, "--output", str(destination)],
        input=backup,
        check=True,
    )


def parse_credentials(contents: str) -> Credentials:
    values: dict[str, str] = {}
    for line in contents.splitlines():
        label, separator, value = line.replace("=", ":", 1).partition(":")
        if separator and label.strip() in {"key", "secret"}:
            values[label.strip()] = value.strip()
    if not values.get("key") or not values.get("secret"):
        raise ValueError("credential file must contain key and secret labels")
    return Credentials(key=values["key"], secret=values["secret"])


def _first_identifier(response: object) -> str:
    if not isinstance(response, dict):
        raise ValueError("OPNsense response is not an object")
    items = response.get("items")
    if isinstance(items, dict) and items:
        identifier = next(iter(items))
        if isinstance(identifier, str) and identifier:
            return identifier
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            identifier = first.get("id")
            if isinstance(identifier, str) and identifier:
                return identifier
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


def main(
    argv: list[str] | None = None,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[[str, Credentials, str, str | None], Client] = HttpsClient,
    artifact_writer: Callable[[Inventory, Path, str], None] = write_inventory_artifacts,
) -> None:
    parser = argparse.ArgumentParser(description="Capture encrypted OPNsense inventory evidence")
    parser.add_argument("--artifact-dir", required=True, type=Path)
    arguments = parser.parse_args(argv)
    environment = environ or os.environ
    required = (
        "OPNSENSE_URL",
        "OPNSENSE_API_KEY",
        "OPNSENSE_API_SECRET",
        "OPNSENSE_CA_FILE",
        "OPNSENSE_BACKUP_RECIPIENT",
    )
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise ValueError(f"missing required environment variables: {', '.join(missing)}")
    credentials = Credentials(environment["OPNSENSE_API_KEY"], environment["OPNSENSE_API_SECRET"])
    client = client_factory(
        environment["OPNSENSE_URL"],
        credentials,
        environment["OPNSENSE_CA_FILE"],
        environment.get("OPNSENSE_TLS_SERVER_NAME"),
    )
    inventory = collect_inventory(client)
    artifact_writer(inventory, arguments.artifact_dir, environment["OPNSENSE_BACKUP_RECIPIENT"])
    print(
        json.dumps(
            {
                "assignment_api_available": inventory.assignment_api_available,
                "backup_id": inventory.backup_id,
                "backup_provider": inventory.backup_provider,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
