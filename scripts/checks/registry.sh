#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in kubectl python; do
  command -v "$tool" >/dev/null || {
    echo "missing required tool: $tool; run nix develop ./flake" >&2
    exit 127
  }
done
python -m scripts.registry plan --lock registry/images.lock.json >/dev/null
python -m scripts.registry check --lock registry/images.lock.json >/dev/null
while IFS= read -r -d '' overlay; do
  kubectl kustomize "$overlay" >/dev/null
done < <(find gitops/registry-cutover/components -mindepth 1 -maxdepth 1 -type d -print0 | sort -z)
