#!/usr/bin/env python3
"""Render the non-secret Jarvis voice topology from Git and optional live state."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = ROOT / "gitops" / "voice"
GATEWAYS = {
    "stt": "wyoming-whisper",
    "tts": "wyoming-chatterbox",
}


def manifest_documents() -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(VOICE_DIR.glob("*.yaml")):
        for document in yaml.safe_load_all(path.read_text()):
            if isinstance(document, dict) and document.get("kind"):
                document["_source"] = str(path.relative_to(ROOT))
                documents.append(document)
    return documents


def backend_preference(document: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for container in (
        document.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    ):
        for env in container.get("env", []):
            if env.get("name") != "WYOMING_BACKENDS":
                continue
            for item in str(env.get("value", "")).split(","):
                if "=" not in item:
                    continue
                name, address = item.split("=", 1)
                host, port = address.rsplit(":", 1)
                result.append({"name": name, "host": host, "port": int(port)})
    return result


def desired_report(documents: list[dict[str, Any]]) -> dict[str, Any]:
    deployments = []
    services = []
    gateways = {}
    for document in documents:
        kind = document.get("kind")
        metadata = document.get("metadata", {})
        name = metadata.get("name")
        if kind == "Deployment":
            deployments.append(
                {
                    "name": name,
                    "namespace": metadata.get("namespace", "default"),
                    "replicas": document.get("spec", {}).get("replicas", 1),
                    "source": document.get("_source"),
                }
            )
            backends = backend_preference(document)
            if backends:
                mode = (
                    "stt"
                    if name == "wyoming-stt-gateway"
                    else "tts"
                    if name == "wyoming-tts-gateway"
                    else None
                )
                if mode:
                    gateways[mode] = {"deployment": name, "backends": backends}
        elif kind == "Service":
            spec = document.get("spec", {})
            services.append(
                {
                    "name": name,
                    "namespace": metadata.get("namespace", "default"),
                    "selector": spec.get("selector", {}),
                    "ports": [
                        {
                            "name": p.get("name"),
                            "port": p.get("port"),
                            "targetPort": p.get("targetPort"),
                        }
                        for p in spec.get("ports", [])
                    ],
                    "source": document.get("_source"),
                }
            )
    return {
        "deployments": sorted(deployments, key=lambda item: item["name"]),
        "gateways": gateways,
        "services": sorted(services, key=lambda item: item["name"]),
        "ha_pipeline": {
            "stt_gateway_service": "wyoming-whisper.voice:10300",
            "tts_gateway_service": "wyoming-chatterbox.voice:10201",
            "conversation_agent": "Jarvis Jev Router",
        },
    }


def run_json(command: list[str]) -> Any:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=15
        )
        return json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def live_report() -> dict[str, Any]:
    deployments = run_json(["kubectl", "-n", "voice", "get", "deploy", "-o", "json"])
    endpoints = run_json(["kubectl", "-n", "voice", "get", "endpoints", "-o", "json"])
    pipeline = run_json(
        [
            "kubectl",
            "-n",
            "home-assistant",
            "exec",
            "deploy/home-assistant",
            "--",
            "cat",
            "/config/.storage/core.config_entries",
        ]
    )
    parsed_pipeline = None
    if isinstance(pipeline, dict):
        try:
            parsed_pipeline = [
                {
                    "domain": entry.get("domain"),
                    "title": entry.get("title"),
                    "stt_engine": entry.get("data", {}).get("stt_engine"),
                    "tts_engine": entry.get("data", {}).get("tts_engine"),
                    "conversation_engine": entry.get("data", {}).get(
                        "conversation_engine"
                    ),
                }
                for entry in pipeline.get("data", {}).get("entries", [])
                if entry.get("domain") in {"assist_pipeline", "conversation"}
            ]
        except (TypeError, json.JSONDecodeError):
            parsed_pipeline = None
    return {
        "deployments": (
            [
                {
                    "name": item.get("metadata", {}).get("name"),
                    "available_replicas": item.get("status", {}).get(
                        "availableReplicas", 0
                    ),
                    "ready_replicas": item.get("status", {}).get("readyReplicas", 0),
                }
                for item in deployments.get("items", [])
            ]
            if isinstance(deployments, dict)
            else None
        ),
        "endpoints": (
            {
                item.get("metadata", {}).get("name"): [
                    address.get("ip")
                    for subset in item.get("subsets", [])
                    for address in subset.get("addresses", [])
                ]
                for item in endpoints.get("items", [])
            }
            if isinstance(endpoints, dict)
            else None
        ),
        "ha_pipeline_engines": parsed_pipeline,
    }


def build_report(include_live: bool = False) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "desired": desired_report(manifest_documents()),
        "live": live_report()
        if include_live
        else {"status": "unknown", "reason": "live inspection not requested"},
    }


def check(report: dict[str, Any]) -> list[str]:
    desired = report["desired"]
    errors = []
    services = {service["name"] for service in desired["services"]}
    for name in ("wyoming-whisper", "wyoming-chatterbox"):
        if name not in services:
            errors.append(f"missing required voice Service: {name}")
    for mode, deployment in (
        ("stt", "wyoming-stt-gateway"),
        ("tts", "wyoming-tts-gateway"),
    ):
        gateway = desired["gateways"].get(mode)
        if (
            not gateway
            or gateway["deployment"] != deployment
            or not gateway["backends"]
        ):
            errors.append(f"missing {mode} gateway preference order")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live", action="store_true", help="add read-only kubectl and HA inspection"
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if desired-state invariants drift"
    )
    args = parser.parse_args(argv)
    report = build_report(args.live)
    print(json.dumps(report, indent=2, sort_keys=True))
    errors = check(report) if args.check else []
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
