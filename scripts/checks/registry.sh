#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in python; do
  command -v "$tool" >/dev/null || {
    echo "missing required tool: $tool; run nix develop ./flake" >&2
    exit 127
  }
done
python -m scripts.registry plan --lock registry/images.lock.json >/dev/null
