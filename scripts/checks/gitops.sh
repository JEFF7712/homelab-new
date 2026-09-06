#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in yamllint kubectl kubeconform; do command -v "$tool" >/dev/null || { echo "missing required tool: $tool; run nix develop ./flake" >&2; exit 127; }; done
yamllint gitops
while IFS= read -r -d '' file; do
  output=$(kubectl kustomize "$(dirname "$file")" | kubeconform -strict -summary -ignore-missing-schemas 2>&1)
  printf '%s\n' "$output"
  if grep -Eq 'Skipped: [1-9]' <<<"$output"; then
    echo 'missing Kubernetes schemas; provision pinned CRD schemas before offline validation' >&2
    exit 69
  fi
done < <(find gitops -name kustomization.yaml -print0 | sort -z)
