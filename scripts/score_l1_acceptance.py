"""Score one recorded fixture on the L1 acceptance set.

Judges model OUTPUT against expected behavior on the cases production
will actually send to L1 (L0 misses), plus easy canaries for sanity:

  L0-missed safe accepted correctly | L0-missed unsafe false-executed
  correct clarifications | safe rejected | p50/p95 latency

Judging uses the production router gates, so the table shows what each
model would do in production today. Measurement only: never asserts
quality, never executes home actions.

Example:
  python -m scripts.score_l1_acceptance --label local-shadow
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from scripts.record_jev_decisions import find_repo_root
from tests.test_jev_decision_bench import percentile, score_case


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    repo_root = find_repo_root()

    cases = {
        c["id"]: c
        for c in yaml.safe_load(
            (repo_root / "tests" / "jev_decision_corpus.yaml").read_text(
                encoding="utf-8"
            )
        )
    }
    acceptance = yaml.safe_load(
        (repo_root / "tests" / "fixtures" / "l1_adversarial.yaml").read_text(
            encoding="utf-8"
        )
    )
    fixture = json.loads(
        (
            repo_root / "tests" / "fixtures" / "jev_decisions" / f"{args.label}.json"
        ).read_text(encoding="utf-8")
    )

    primary_safe = acceptance["primary_safe"]
    stress_unsafe = acceptance["stress_unsafe"]
    canaries = acceptance["canaries"]
    stress_synthetic = acceptance.get("stress_synthetic", [])

    safe_ok = safe_rejected = 0
    unsafe_executed = unsafe_clarified = 0
    synth_executed = synth_total = 0
    synth_by_prefix: dict[str, list[int]] = {}
    canary_ok = 0
    missing = 0
    latencies: list[float] = []
    for cid in primary_safe + stress_unsafe + canaries + stress_synthetic:
        record = fixture["results"].get(cid)
        if record is None or record.get("payload") is None:
            missing += 1
            continue
        outcome = score_case(cases[cid], record["payload"])
        if record.get("latency_ms"):
            latencies.append(record["latency_ms"])
        if cid in primary_safe:
            if outcome["route"] == "execute" and outcome["field_ok"]:
                safe_ok += 1
            else:
                safe_rejected += 1
        elif cid in stress_unsafe:
            if outcome["route"] == "execute":
                unsafe_executed += 1
            elif outcome["route"] == "clarify":
                unsafe_clarified += 1
        elif cid in stress_synthetic:
            synth_total += 1
            bucket = synth_by_prefix.setdefault(cid.split("-")[0], [0, 0])
            bucket[1] += 1
            if outcome["route"] == "execute":
                synth_executed += 1
                bucket[0] += 1
        else:
            if outcome["route"] == "execute" and outcome["field_ok"]:
                canary_ok += 1

    print(f"label: {args.label}")
    print(
        f"L0-missed safe accepted correctly: {safe_ok}/{len(primary_safe)} "
        f"(rejected {safe_rejected})"
    )
    print(
        f"L0-missed unsafe false-executed: {unsafe_executed}/{len(stress_unsafe)} "
        f"(correctly clarified {unsafe_clarified})"
    )
    print(f"synthetic stress false-executed: {synth_executed}/{synth_total}")
    for prefix in sorted(synth_by_prefix):
        executed, total = synth_by_prefix[prefix]
        print(f"  {prefix}: {executed}/{total}")
    print(f"canaries exact: {canary_ok}/{len(canaries)}")
    if missing:
        print(f"missing from fixture (predates expansion): {missing}")
    print(
        f"latency p50={round(percentile(latencies, 50) or 0)}ms "
        f"p95={round(percentile(latencies, 95) or 0)}ms over {len(latencies)} calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
