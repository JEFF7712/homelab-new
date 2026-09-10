from __future__ import annotations

import ipaddress
import json
import os
import sys


def render_bulbs(bulbs_json: str) -> str:
    try:
        bulbs = json.loads(bulbs_json)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"ROKU_BRIDGE_BULBS_JSON is not valid JSON: {error}"
        ) from error
    if not isinstance(bulbs, list) or not bulbs:
        raise ValueError("ROKU_BRIDGE_BULBS_JSON must be a non-empty list")

    lines = ["bulbs:"]
    for entry in bulbs:
        name = str(entry.get("name", "")).strip()
        mac = str(entry.get("mac", "")).replace(":", "").upper()
        ip = str(entry.get("ip", ""))
        enr = str(entry.get("enr", ""))
        if not name:
            raise ValueError("each bulb needs a non-empty name")
        if len(mac) != 12 or any(c not in "0123456789ABCDEF" for c in mac):
            raise ValueError(f"bulb {name!r} has an invalid mac (want 12 hex chars)")
        try:
            ipaddress.IPv4Address(ip)
        except ipaddress.AddressValueError as error:
            raise ValueError(f"bulb {name!r} has an invalid ip: {error}") from error
        if len(enr) != 16:
            raise ValueError(f"bulb {name!r} has an invalid enr (want 16 chars)")
        lines += [
            f"  - name: {name}",
            f"    mac: {mac}",
            f"    ip: {ip}",
            f"    enr: {enr}",
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        print(render_bulbs(os.environ["ROKU_BRIDGE_BULBS_JSON"]), end="")
    except (KeyError, ValueError) as error:
        print(error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
