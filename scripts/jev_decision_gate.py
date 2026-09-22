#!/usr/bin/env python3
"""Fail CI when a recorded Jev model fixture violates release safety gates."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

bench = importlib.import_module("tests.test_jev_decision_bench")
CORPUS_PATH = bench.CORPUS_PATH
FIXTURE_DIR = bench.FIXTURE_DIR
gate_failures = bench.gate_failures
load_fixtures = bench.load_fixtures
score_case = bench.score_case
summarize = bench.summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", action="append", dest="models")
    args = parser.parse_args(argv)
    cases = {case["id"]: case for case in yaml.safe_load(CORPUS_PATH.read_text())}
    fixtures = load_fixtures()
    selected = args.models or sorted(fixtures)
    if not selected:
        print(f"no recorded fixtures found in {FIXTURE_DIR}", file=sys.stderr)
        return 2
    failed = False
    for model in selected:
        fixture = fixtures.get(model)
        if fixture is None:
            print(f"{model}: fixture not found", file=sys.stderr)
            failed = True
            continue
        records = fixture["results"]
        outcomes = [
            score_case(cases[case_id], record["payload"])
            for case_id, record in records.items()
        ]
        latencies = [
            float(record["latency_ms"])
            for outcome, record in zip(outcomes, records.values())
            if outcome["source"] == "l1"
            and isinstance(record.get("latency_ms"), (int, float))
        ]
        summary = summarize(outcomes, latencies)
        errors = gate_failures(summary, outcomes)
        print(
            json.dumps(
                {"model": model, "summary": summary, "gate_failures": errors},
                sort_keys=True,
            )
        )
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
