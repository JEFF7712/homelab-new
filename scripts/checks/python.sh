#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in ruff pyright python; do command -v "$tool" >/dev/null || { echo "missing required tool: $tool; run nix develop ./flake" >&2; exit 127; }; done
ruff format --check scripts opnsense_reconciler tests
ruff check --select E,F,I,UP --ignore E501 scripts opnsense_reconciler tests
pyright scripts/agent scripts/registry scripts/deploy_fleet.py scripts/home_assistant opnsense_reconciler
python -m unittest discover -s tests -v
