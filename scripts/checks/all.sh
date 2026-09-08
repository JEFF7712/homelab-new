#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
bash scripts/checks/agent-workflows.sh
bash scripts/checks/python.sh
bash scripts/checks/registry.sh
bash scripts/checks/nix.sh all
bash scripts/checks/gitops.sh
bash scripts/checks/tofu.sh
python scripts/checks/docs.py
python scripts/checks/whitespace.py
gitleaks detect --source . --redact
nix flake check 'path:.?dir=flake' --no-write-lock-file
