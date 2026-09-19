"""Live Jarvis routing eval through assist_pipeline/run.

Runs every corpus case as text input from the intent stage to the intent
stage: no wake word, no STT, no side effects. Local-path cases must route
locally with the expected reply and targets; llm-path cases must fall
through to the LLM. Full LLM behavior (tools, phrasing) stays manual.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from scripts.home_assistant.client import HomeAssistantClient

CORPUS_PATH = Path("tests/jarvis_voice_eval_corpus.yaml")
DEFAULT_URL = "http://10.0.40.13:8123"


def find_repo_root() -> Path:
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return Path(res.stdout.strip())
    except Exception:
        pass
    return Path.cwd()


def resolve_token(token_arg: str | None, token_file_arg: str | None) -> str:
    if token_arg:
        return token_arg
    if token_file_arg and os.path.isfile(token_file_arg):
        return Path(token_file_arg).read_text(encoding="utf-8").strip()
    env_token = os.environ.get("HASS_TOKEN")
    if env_token:
        return env_token
    env_file = os.environ.get("HASS_TOKEN_FILE")
    if env_file and os.path.isfile(env_file):
        return Path(env_file).read_text(encoding="utf-8").strip()
    local_token = find_repo_root() / ".agent-state" / "home-assistant" / "token"
    if local_token.is_file():
        return local_token.read_text(encoding="utf-8").strip()
    return ""


def load_corpus(repo_root: Path) -> list[dict[str, Any]]:
    with open(repo_root / CORPUS_PATH, encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"Corpus at {CORPUS_PATH} is empty or not a list")
    return entries


def collect_run_events(
    ws: Any, payload: dict[str, Any], timeout_s: float
) -> list[dict[str, Any]]:
    msg_id = ws._msg_id
    ws._msg_id += 1
    ws._send_frame(json.dumps({"id": msg_id, **payload}))
    events: list[dict[str, Any]] = []
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        opcode, data = ws._read_frame()
        if opcode != 0x01:
            continue
        msg = json.loads(data.decode("utf-8"))
        if msg.get("id") != msg_id:
            continue
        if msg.get("type") == "result":
            if not msg.get("success", True):
                err = msg.get("error", {})
                raise RuntimeError(
                    f"Pipeline run rejected ({err.get('code')}): {err.get('message')}"
                )
            continue
        event = msg.get("event")
        if isinstance(event, dict):
            events.append(event)
            if event.get("type") == "run-end":
                return events
    raise TimeoutError(f"No run-end within {timeout_s}s for {payload}")


def intent_end(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in events:
        if event.get("type") == "intent-end":
            data = event.get("data")
            if isinstance(data, dict):
                return data
    return None


def speech_of(data: dict[str, Any]) -> str | None:
    try:
        return data["intent_output"]["response"]["speech"]["plain"]["speech"]
    except (KeyError, TypeError):
        return None


def success_ids_of(data: dict[str, Any]) -> list[str] | None:
    try:
        success = data["intent_output"]["response"]["data"]["success"]
    except (KeyError, TypeError):
        return None
    if not isinstance(success, list):
        return None
    ids: list[str] = []
    for s in success:
        if isinstance(s, dict) and isinstance(s.get("id"), str):
            ids.append(s["id"])
    return ids


def failed_of(data: dict[str, Any]) -> list[Any] | None:
    try:
        failed = data["intent_output"]["response"]["data"]["failed"]
    except (KeyError, TypeError):
        return None
    return failed if isinstance(failed, list) else None


def evaluate(case: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    data = intent_end(events)
    if data is None:
        return {
            "id": case.get("id"),
            "say": case.get("say"),
            "path": case.get("path"),
            "ok": False,
            "failures": ["no intent-end event in run"],
        }
    processed = data.get("processed_locally")
    if case.get("path") == "local":
        if processed is not True:
            failures.append(f"expected local routing, processed_locally={processed}")
        else:
            expected_response = case.get("response")
            speech = speech_of(data)
            if case.get("dynamic"):
                if not speech:
                    failures.append("expected non-empty dynamic reply, got none")
            elif speech != expected_response:
                failures.append(
                    f"reply mismatch: expected {expected_response!r}, got {speech!r}"
                )
            success_ids = success_ids_of(data)
            if success_ids is None:
                failures.append("intent-end has no success target list")
            elif case.get("targets"):
                outside = sorted(set(success_ids) - set(case.get("targets", [])))
                if outside:
                    failures.append(f"action outside targets: {outside}")
            failed = failed_of(data)
            if failed:
                failures.append(f"failed targets: {failed}")
    else:
        if processed is not False:
            failures.append(f"expected LLM fallthrough, processed_locally={processed}")
    return {
        "id": case.get("id"),
        "say": case.get("say"),
        "path": case.get("path"),
        "ok": not failures,
        "failures": failures,
    }


def run_case(
    url: str,
    token: str,
    timeout_s: float,
    pipeline_id: str,
    case: dict[str, Any],
) -> dict[str, Any]:
    client = HomeAssistantClient(base_url=url, token=token, timeout=timeout_s)
    try:
        ws = client._get_ws()
        events = collect_run_events(
            ws,
            {
                "type": "assist_pipeline/run",
                "pipeline": pipeline_id,
                "start_stage": "intent",
                "end_stage": "intent",
                "input": {"text": case["say"]},
            },
            timeout_s,
        )
    except Exception as exc:
        result = {
            "id": case.get("id"),
            "say": case.get("say"),
            "path": case.get("path"),
            "ok": False,
            "failures": [f"run error: {exc}"],
        }
    else:
        result = evaluate(case, events)
    finally:
        if client._ws is not None:
            client._ws.close()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live Jarvis routing eval")
    parser.add_argument("--url", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--token-file", default=None)
    parser.add_argument("--pipeline", default=None)
    parser.add_argument("--select", action="append", default=None)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--pause",
        type=float,
        default=5.0,
        help="Seconds to wait between cases (Govee cloud rate-limits bursts)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo_root = find_repo_root()
    try:
        corpus = load_corpus(repo_root)
    except Exception as exc:
        print(f"Cannot load corpus: {exc}", file=sys.stderr)
        return 2
    if args.select:
        wanted = set(args.select)
        corpus = [c for c in corpus if c.get("id") in wanted]
        if not corpus:
            print(f"No corpus cases match {sorted(wanted)}", file=sys.stderr)
            return 2

    url = args.url or os.environ.get("HASS_URL", DEFAULT_URL)
    token = resolve_token(args.token, args.token_file)
    client = HomeAssistantClient(base_url=url, token=token, timeout=args.timeout)
    try:
        pipelines = client._get_ws().call("assist_pipeline/pipeline/list")
        pipeline_id = args.pipeline or pipelines.get("preferred_pipeline")
        if not pipeline_id:
            print("No preferred pipeline and none given", file=sys.stderr)
            return 2
    except Exception as exc:
        print(f"Pipeline lookup failed: {exc}", file=sys.stderr)
        return 2

    results = []
    for i, case in enumerate(corpus):
        if i > 0 and args.pause > 0:
            time.sleep(args.pause)
        results.append(run_case(url, token, args.timeout, pipeline_id, case))
    passed = sum(1 for r in results if r["ok"])
    payload = {
        "status": "pass" if passed == len(results) else "fail",
        "pipeline": pipeline_id,
        "passed": passed,
        "total": len(results),
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for r in results:
            mark = "PASS" if r["ok"] else "FAIL"
            print(f"[{mark}] {r['id']}: {r['say']}")
            for f in r["failures"]:
                print(f"       - {f}")
        print(f"\nRouting: {passed}/{len(results)} correct")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
