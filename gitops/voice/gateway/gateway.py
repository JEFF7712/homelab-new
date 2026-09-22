"""Protocol-aware Wyoming gateway with ordered backend failover and metrics."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread


def encode_event(event: dict) -> bytes:
    data = json.dumps(event.get("data") or {}).encode() if event.get("data") else b""
    payload = event.get("payload") or b""
    header = {"type": event.get("type")}
    if data:
        header["data_length"] = len(data)
    if payload:
        header["payload_length"] = len(payload)
    return json.dumps(header, separators=(",", ":")).encode() + b"\n" + data + payload


async def read_event(reader: asyncio.StreamReader) -> dict | None:
    line = await reader.readline()
    if not line:
        return None
    header = json.loads(line)
    data_length = int(header.get("data_length") or 0)
    payload_length = int(header.get("payload_length") or 0)
    data = json.loads(await reader.readexactly(data_length)) if data_length else {}
    payload = await reader.readexactly(payload_length) if payload_length else b""
    return {"type": header.get("type"), "data": data, "payload": payload}


@dataclass
class Backend:
    name: str
    host: str
    port: int
    failures: int = 0
    open_until: float = 0.0
    healthy: bool = False


class Metrics:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self._lock = Lock()
        self.counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self.sums: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, int]] = {}

    @staticmethod
    def _labels(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(labels.items()))

    def inc(self, name: str, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0.0) + 1

    def observe(self, name: str, value: float, **labels: str) -> None:
        key = (name, self._labels(labels))
        with self._lock:
            total, count = self.sums.get(key, (0.0, 0))
            self.sums[key] = (total + value, count + 1)

    def render(self, backends: list[Backend]) -> bytes:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self.counters.items()):
                lines.append(f"{name}{format_labels(labels)} {value}")
            for (name, labels), (total, count) in sorted(self.sums.items()):
                lines.append(f"{name}_sum{format_labels(labels)} {total}")
                lines.append(f"{name}_count{format_labels(labels)} {count}")
        now = time.monotonic()
        for backend in backends:
            labels = format_labels((("backend", backend.name), ("mode", self.mode)))
            available = backend.healthy and backend.open_until <= now
            lines.append(f"jarvis_gateway_backend_available{labels} {int(available)}")
        return ("\n".join(lines) + "\n").encode()


def format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    body = ",".join(f'{key}="{value}"' for key, value in labels)
    return "{" + body + "}"


@dataclass
class TurnMetrics:
    mode: str
    backend: str
    metrics: Metrics
    vad_end: float | None = None
    synthesis_start: float | None = None
    first_audio: float | None = None
    audio_bytes: int = 0
    audio_rate: int = 0
    audio_width: int = 0
    audio_channels: int = 0

    def client_event(self, event: dict) -> None:
        kind = event["type"]
        if self.mode == "stt" and kind == "audio-stop":
            self.vad_end = time.monotonic()
        if self.mode == "tts" and kind in {"synthesize", "synthesize-stop"}:
            self.synthesis_start = time.monotonic()

    def backend_event(self, event: dict) -> None:
        kind = event["type"]
        now = time.monotonic()
        labels = {"backend": self.backend}
        if self.mode == "stt" and kind == "transcript" and self.vad_end is not None:
            self.metrics.observe(
                "jarvis_stt_vad_to_final_seconds", now - self.vad_end, **labels
            )
        if self.mode == "tts":
            if kind == "audio-start":
                self.first_audio = now
                data = event["data"]
                self.audio_rate = int(data.get("rate") or 0)
                self.audio_width = int(data.get("width") or 0)
                self.audio_channels = int(data.get("channels") or 0)
                if self.synthesis_start is not None:
                    self.metrics.observe(
                        "jarvis_tts_time_to_first_audio_seconds",
                        now - self.synthesis_start,
                        **labels,
                    )
            elif kind == "audio-chunk":
                self.audio_bytes += len(event["payload"])
            elif kind == "error":
                self.metrics.inc("jarvis_tts_synthesis_failures_total", backend=self.backend)
            elif kind == "audio-stop" and self.synthesis_start is not None:
                denominator = self.audio_rate * self.audio_width * self.audio_channels
                audio_seconds = self.audio_bytes / denominator if denominator else 0.0
                wall = now - self.synthesis_start
                if audio_seconds:
                    self.metrics.observe(
                        "jarvis_tts_synthesis_realtime_factor",
                        wall / audio_seconds,
                        **labels,
                    )
                    self.metrics.observe(
                        "jarvis_tts_generated_audio_seconds", audio_seconds, **labels
                    )
                self.metrics.inc("jarvis_tts_synthesis_success_total", backend=self.backend)


@dataclass
class Gateway:
    mode: str
    backends: list[Backend]
    metrics: Metrics
    failure_threshold: int = 2
    cooldown_seconds: float = 30.0
    connect_timeout: float = 1.0
    _selection_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def probe(self, backend: Backend) -> None:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(backend.host, backend.port),
                self.connect_timeout,
            )
            writer.close()
            await writer.wait_closed()
            backend.healthy = True
            if backend.open_until <= time.monotonic():
                backend.failures = 0
        except (OSError, TimeoutError):
            backend.healthy = False

    async def health_loop(self) -> None:
        while True:
            await asyncio.gather(*(self.probe(backend) for backend in self.backends))
            await asyncio.sleep(5)

    async def connect_backend(
        self,
        exclude: set[str] | None = None,
    ) -> tuple[Backend, asyncio.StreamReader, asyncio.StreamWriter]:
        async with self._selection_lock:
            now = time.monotonic()
            for backend in self.backends:
                if exclude and backend.name in exclude:
                    continue
                if backend.open_until > now:
                    continue
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(backend.host, backend.port),
                        self.connect_timeout,
                    )
                    backend.healthy = True
                    backend.failures = 0
                    self.metrics.inc(
                        "jarvis_gateway_connections_total",
                        mode=self.mode,
                        backend=backend.name,
                    )
                    if exclude:
                        self.metrics.inc(
                            "jarvis_gateway_fallbacks_total",
                            mode=self.mode,
                            backend=backend.name,
                        )
                    return backend, reader, writer
                except (OSError, TimeoutError):
                    backend.failures += 1
                    backend.healthy = False
                    self.metrics.inc(
                        "jarvis_gateway_backend_failures_total",
                        mode=self.mode,
                        backend=backend.name,
                    )
                    if backend.failures >= self.failure_threshold:
                        backend.open_until = now + self.cooldown_seconds
            raise ConnectionError("no Wyoming backend is available")

    async def handle_tts(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        """Buffer one small synthesis request so pre-audio failure can retry."""
        first = await read_event(client_reader)
        if first is None:
            client_writer.close()
            await client_writer.wait_closed()
            return
        buffered = [first]
        if first["type"] == "synthesize-start":
            while True:
                event = await read_event(client_reader)
                if event is None:
                    break
                buffered.append(event)
                if event["type"] == "synthesize-stop":
                    break
        if first["type"] not in {"synthesize", "synthesize-start"}:
            backend, backend_reader, backend_writer = await self.connect_backend()
            for event in buffered:
                backend_writer.write(encode_event(event))
            await backend_writer.drain()
            while (event := await read_event(backend_reader)) is not None:
                client_writer.write(encode_event(event))
                await client_writer.drain()
                if event["type"] in {"info", "audio-stop", "error"}:
                    break
            backend_writer.close()
            client_writer.close()
            await asyncio.gather(backend_writer.wait_closed(), client_writer.wait_closed())
            return

        attempted: set[str] = set()
        audio_started = False
        try:
            while True:
                backend, backend_reader, backend_writer = await self.connect_backend(attempted)
                attempted.add(backend.name)
                for event in buffered:
                    backend_writer.write(encode_event(event))
                await backend_writer.drain()
                retry = False
                while True:
                    event = await read_event(backend_reader)
                    if event is None:
                        retry = not audio_started
                        break
                    if event["type"] == "audio-start":
                        audio_started = True
                    if event["type"] == "error" and not audio_started:
                        retry = True
                        break
                    client_writer.write(encode_event(event))
                    await client_writer.drain()
                    if event["type"] in {"audio-stop", "error"}:
                        break
                backend_writer.close()
                await backend_writer.wait_closed()
                if not retry or audio_started or len(attempted) >= len(self.backends):
                    break
        except (OSError, ConnectionError, asyncio.IncompleteReadError, ValueError):
            self.metrics.inc("jarvis_gateway_stream_failures_total", mode=self.mode)
        finally:
            client_writer.close()
            await client_writer.wait_closed()

    async def handle(
        self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter
    ) -> None:
        if self.mode == "tts":
            await self.handle_tts(client_reader, client_writer)
            return
        try:
            backend, backend_reader, backend_writer = await self.connect_backend()
        except ConnectionError:
            self.metrics.inc(
                "jarvis_gateway_rejected_connections_total", mode=self.mode
            )
            client_writer.close()
            await client_writer.wait_closed()
            return
        turn = TurnMetrics(self.mode, backend.name, self.metrics)

        async def forward(reader, writer, observe) -> None:
            while (event := await read_event(reader)) is not None:
                observe(event)
                writer.write(encode_event(event))
                await writer.drain()

        tasks = {
            asyncio.create_task(
                forward(client_reader, backend_writer, turn.client_event)
            ),
            asyncio.create_task(
                forward(backend_reader, client_writer, turn.backend_event)
            ),
        }
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            try:
                task.result()
            except (OSError, ConnectionError, asyncio.IncompleteReadError, ValueError):
                self.metrics.inc(
                    "jarvis_gateway_stream_failures_total",
                    mode=self.mode,
                    backend=backend.name,
                )
        backend_writer.close()
        client_writer.close()
        await asyncio.gather(
            backend_writer.wait_closed(),
            client_writer.wait_closed(),
            return_exceptions=True,
        )


def parse_backends(value: str) -> list[Backend]:
    result = []
    for item in value.split(","):
        name, address = item.split("=", 1)
        host, port = address.rsplit(":", 1)
        result.append(Backend(name.strip(), host.strip(), int(port)))
    if not result:
        raise ValueError("at least one backend is required")
    return result


def serve_metrics(metrics: Metrics, backends: list[Backend], port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/metrics", "/healthz"}:
                self.send_error(404)
                return
            body = metrics.render(backends) if self.path == "/metrics" else b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args: object) -> None:
            pass

    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


async def amain() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("stt", "tts"), required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--metrics-port", type=int, default=8000)
    args = parser.parse_args()
    backends = parse_backends(os.environ["WYOMING_BACKENDS"])
    metrics = Metrics(args.mode)
    gateway = Gateway(args.mode, backends, metrics)
    Thread(
        target=serve_metrics, args=(metrics, backends, args.metrics_port), daemon=True
    ).start()
    asyncio.create_task(gateway.health_loop())
    server = await asyncio.start_server(gateway.handle, "0.0.0.0", args.port)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(amain())
