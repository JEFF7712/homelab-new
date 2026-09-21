"""Record Jev decision-model outputs for the offline bench.

Posts every corpus utterance through router.build_request to one
/v1/systemone-compatible endpoint and writes
tests/fixtures/jev_decisions/<label>.json for
tests/test_jev_decision_bench.py to score. Measurement only: never asserts
quality, never executes home actions.

Examples:
  # local shadow via port-forward (kubectl port-forward svc/local-decision 8080)
  python -m scripts.record_jev_decisions --label local-shadow \\
      --endpoint http://127.0.0.1:8080/v1/systemone
  # hosted reference (needs TYPESAFE_API_KEY in the environment)
  python -m scripts.record_jev_decisions --label jev-1-13-0 \\
      --endpoint https://api.typesafe.ai/v1/systemone --api-key-env TYPESAFE_API_KEY
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import time
import types
import urllib.request
from pathlib import Path

PACKAGE_DIR = Path("home-assistant") / "custom_components" / "jarvis_jev"


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


def load_router(repo_root: Path):
    package = types.ModuleType("jarvis_jev")
    package.__path__ = [str(repo_root / PACKAGE_DIR)]
    sys.modules["jarvis_jev"] = package
    for name in ("const", "router"):
        spec = importlib.util.spec_from_file_location(
            f"jarvis_jev.{name}", repo_root / PACKAGE_DIR / f"{name}.py"
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"jarvis_jev.{name}"] = module
        spec.loader.exec_module(module)
    return sys.modules["jarvis_jev.router"]


def post(endpoint: str, headers: dict, request: dict, timeout: float) -> dict:
    started = time.monotonic()
    try:
        body = json.dumps(request).encode()
        req = urllib.request.Request(
            endpoint, data=body, headers={"Content-Type": "application/json", **headers}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
        return {
            "latency_ms": (time.monotonic() - started) * 1000,
            "payload": payload,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "latency_ms": None,
            "payload": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, help="fixture name, e.g. von-1-0")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8080/v1/systemone")
    parser.add_argument("--api-key-env", default=None)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--corpus", default="tests/jev_decision_corpus.yaml")
    parser.add_argument("--out-dir", default="tests/fixtures/jev_decisions")
    args = parser.parse_args(argv)

    repo_root = find_repo_root()
    router = load_router(repo_root)
    try:
        import yaml
    except ImportError:
        print("pyyaml is required (nix develop ./flake)", file=sys.stderr)
        return 2
    with open(repo_root / args.corpus, encoding="utf-8") as f:
        cases = yaml.safe_load(f)

    headers: dict[str, str] = {}
    if args.api_key_env:
        api_key = os.environ.get(args.api_key_env, "")
        if not api_key:
            print(f"{args.api_key_env} is not set", file=sys.stderr)
            return 2
        headers["Authorization"] = f"Bearer {api_key}"

    results: dict[str, dict] = {}
    errors = 0
    for case in cases:
        record = post(
            args.endpoint, headers, router.build_request(case["say"]), args.timeout
        )
        if record.get("payload") is None:
            errors += 1
        results[case["id"]] = record
        status = "err" if record.get("payload") is None else "ok"
        print(f"[{status}] {case['id']}")

    out_dir = repo_root / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "model": args.label,
                "endpoint": args.endpoint,
                "corpus_cases": len(cases),
                "errors": errors,
                "results": results,
            },
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")
    print(f"\nwrote {out_path} ({len(cases) - errors}/{len(cases)} ok)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
