#!/usr/bin/env python3
"""Prometheus exporter for NVIDIA GPU metrics using nvidia-smi."""

import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

QUERY_CMD = [
    "nvidia-smi",
    (
        "--query-gpu=index,name,temperature.gpu,utilization.gpu,utilization.memory,"
        "memory.total,memory.used,memory.free,fan.speed"
    ),
    "--format=csv,noheader,nounits",
]


def safe_float(v: str, scale: float = 1.0) -> float:
    try:
        return float(v.strip()) * scale
    except (ValueError, TypeError):
        return 0.0


def collect_metrics() -> str:
    lines = [
        "# HELP nvidia_smi_gpu_temp_celsius GPU temperature in Celsius",
        "# TYPE nvidia_smi_gpu_temp_celsius gauge",
        "# HELP nvidia_smi_utilization_gpu_ratio GPU utilization ratio (0 to 1)",
        "# TYPE nvidia_smi_utilization_gpu_ratio gauge",
        "# HELP nvidia_smi_utilization_memory_ratio GPU memory utilization ratio (0 to 1)",
        "# TYPE nvidia_smi_utilization_memory_ratio gauge",
        "# HELP nvidia_smi_memory_total_bytes Total GPU memory in bytes",
        "# TYPE nvidia_smi_memory_total_bytes gauge",
        "# HELP nvidia_smi_memory_used_bytes Used GPU memory in bytes",
        "# TYPE nvidia_smi_memory_used_bytes gauge",
        "# HELP nvidia_smi_memory_free_bytes Free GPU memory in bytes",
        "# TYPE nvidia_smi_memory_free_bytes gauge",
        "# HELP nvidia_smi_fan_speed_ratio GPU fan speed ratio (0 to 1)",
        "# TYPE nvidia_smi_fan_speed_ratio gauge",
    ]
    output = subprocess.check_output(QUERY_CMD, text=True).strip()
    for row in output.splitlines():
        parts = [p.strip() for p in row.split(",")]
        if len(parts) < 9:
            continue
        idx, name, temp, gpu_util, mem_util, mem_tot, mem_used, mem_free, fan = parts[
            :9
        ]
        labels = f'gpu="{idx}",name="{name}"'
        lines.append(f"nvidia_smi_gpu_temp_celsius{{{labels}}} {safe_float(temp)}")
        lines.append(
            f"nvidia_smi_utilization_gpu_ratio{{{labels}}} {safe_float(gpu_util, 0.01):.4f}"
        )
        lines.append(
            f"nvidia_smi_utilization_memory_ratio{{{labels}}} {safe_float(mem_util, 0.01):.4f}"
        )
        lines.append(
            f"nvidia_smi_memory_total_bytes{{{labels}}} {safe_float(mem_tot, 1024 * 1024):.0f}"
        )
        lines.append(
            f"nvidia_smi_memory_used_bytes{{{labels}}} {safe_float(mem_used, 1024 * 1024):.0f}"
        )
        lines.append(
            f"nvidia_smi_memory_free_bytes{{{labels}}} {safe_float(mem_free, 1024 * 1024):.0f}"
        )
        lines.append(
            f"nvidia_smi_fan_speed_ratio{{{labels}}} {safe_float(fan, 0.01):.4f}"
        )
    return "\n".join(lines) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path not in ("/metrics", "/"):
            self.send_response(404)
            self.end_headers()
            return
        try:
            content = collect_metrics().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:  # noqa: BLE001
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        pass


def main() -> None:
    port = int(os.environ.get("PORT", "9835"))
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
