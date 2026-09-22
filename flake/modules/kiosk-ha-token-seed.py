"""Seed the Jarvis kiosk Home Assistant token after every boot.

The homelab uses a tmpfs root, so /home/kiosk (and the Chromium profile
holding the face's long-lived token) is recreated empty on every reboot.
This script re-stores the token from a /persist secret file into the
kiosk browser's localStorage over its local DevTools port, then reloads
the face so it authenticates without prompting.

Only file paths travel on the command line; the token itself is read
from disk inside this process and never appears in argv or the journal.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import struct
import sys
import time
import urllib.request
from typing import Any


def list_targets(cdp_http: str, timeout: float) -> list[dict[str, Any]]:
    with urllib.request.urlopen(cdp_http + "/json", timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, list):
        raise RuntimeError("unexpected debugger target list")
    return [t for t in data if isinstance(t, dict)]


def find_jarvis_target(targets: list[dict[str, Any]]) -> dict[str, Any] | None:
    for target in targets:
        if target.get("type") != "page":
            continue
        url = str(target.get("url", ""))
        if "/local/jarvis/" in url and target.get("webSocketDebuggerUrl"):
            return target
    return None


def ws_connect(host: str, port: int, path: str, timeout: float) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        sock.sendall(request.encode("ascii"))
        header = b""
        while b"\r\n\r\n" not in header:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("debugger handshake closed")
            header += chunk
        status = header.split(b"\r\n")[0].decode("ascii", errors="ignore")
        if "101" not in status:
            raise RuntimeError(f"debugger handshake rejected: {status}")
        return sock
    except Exception:
        sock.close()
        raise


def ws_send(sock: socket.socket, message: dict[str, Any]) -> None:
    payload = json.dumps(message).encode("utf-8")
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    frame = bytearray([0x81])
    length = len(payload)
    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack("!Q", length))
    sock.sendall(bytes(frame) + mask + masked)


def ws_recv(sock: socket.socket, buf: bytearray, timeout: float) -> dict[str, Any]:
    sock.settimeout(timeout)
    while True:
        while len(buf) < 2:
            chunk = sock.recv(4096)
            if not chunk:
                raise RuntimeError("debugger connection closed")
            buf += chunk
        opcode = buf[0] & 0x0F
        masked = bool(buf[1] & 0x80)
        length = buf[1] & 0x7F
        offset = 2
        if length == 126:
            while len(buf) < 4:
                buf += sock.recv(4096)
            length = struct.unpack("!H", bytes(buf[2:4]))[0]
            offset = 4
        elif length == 127:
            while len(buf) < 10:
                buf += sock.recv(4096)
            length = struct.unpack("!Q", bytes(buf[2:10]))[0]
            offset = 10
        mask = b""
        if masked:
            while len(buf) < offset + 4:
                buf += sock.recv(4096)
            mask = bytes(buf[offset : offset + 4])
            offset += 4
        while len(buf) < offset + length:
            buf += sock.recv(offset + length - len(buf))
        data = bytes(buf[offset : offset + length])
        del buf[: offset + length]
        if mask:
            data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
        if opcode == 0x8:
            raise RuntimeError("debugger connection closed by peer")
        if opcode != 0x1:
            continue
        decoded = json.loads(data.decode("utf-8"))
        if isinstance(decoded, dict):
            return decoded


def evaluate(
    sock: socket.socket, message_id: int, expression: str, timeout: float
) -> Any:
    ws_send(
        sock,
        {
            "id": message_id,
            "method": "Runtime.evaluate",
            "params": {"expression": expression, "returnByValue": True},
        },
    )
    buf = bytearray()
    while True:
        response = ws_recv(sock, buf, timeout)
        if response.get("id") == message_id:
            result = response.get("result", {}).get("result", {})
            if response.get("error") or result.get("subtype") == "error":
                raise RuntimeError(f"evaluation failed: {response}")
            return result.get("value")


def seed_token(ws_url: str, token: str, timeout: float) -> int:
    from urllib.parse import urlsplit

    parts = urlsplit(ws_url)
    host = parts.hostname or "127.0.0.1"
    port = parts.port or 9222
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    sock = ws_connect(host, port, path, timeout)
    try:
        stored = evaluate(
            sock,
            1,
            "localStorage.setItem('jarvis_token', "
            + json.dumps(token)
            + "); (localStorage.getItem('jarvis_token') || '').length",
            timeout,
        )
        if not isinstance(stored, int) or stored != len(token):
            raise RuntimeError("token round-trip check failed")
        evaluate(sock, 2, "location.reload()", timeout)
        return stored
    finally:
        sock.close()


def wait_for_jarvis_page(cdp_http: str, timeout: float, deadline: float) -> str:
    while True:
        try:
            target = find_jarvis_target(list_targets(cdp_http, timeout))
        except Exception:
            target = None
        if target is not None:
            url = target.get("webSocketDebuggerUrl")
            if isinstance(url, str) and url:
                return url
        if time.monotonic() >= deadline:
            raise TimeoutError("timed out waiting for the Jarvis kiosk page")
        time.sleep(2.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token-file", required=True)
    parser.add_argument("--cdp", default="http://127.0.0.1:9222")
    parser.add_argument("--wait-seconds", type=float, default=180.0)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args(argv)

    try:
        with open(args.token_file, encoding="utf-8") as handle:
            token = handle.read().strip()
    except OSError as exc:
        print(f"cannot read token file: {exc}", file=sys.stderr)
        return 1
    if not token:
        print("token file is empty", file=sys.stderr)
        return 1

    try:
        ws_url = wait_for_jarvis_page(
            args.cdp, args.timeout, time.monotonic() + args.wait_seconds
        )
        stored = seed_token(ws_url, token, args.timeout)
    except (OSError, RuntimeError, TimeoutError) as exc:
        print(f"token seeding failed: {exc}", file=sys.stderr)
        return 1
    print(f"seeded kiosk token ({stored} chars), face reloading")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
