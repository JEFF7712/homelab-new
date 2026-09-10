#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export SKIP_TESTS=1
export SKIP_NIX_EVAL=1
bash scripts/checks/agent-workflows.sh
bash scripts/checks/python.sh
bash scripts/checks/registry.sh
bash scripts/checks/nix.sh all
bash scripts/checks/gitops.sh
bash scripts/checks/tofu.sh
bash scripts/checks/home-assistant.sh
python scripts/checks/docs.py
python scripts/checks/whitespace.py
gitleaks detect --source . --redact
nix flake check 'path:.?dir=flake' --no-write-lock-file
