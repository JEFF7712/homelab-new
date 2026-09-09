#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in yamllint kubectl kubeconform; do command -v "$tool" >/dev/null || { echo "missing required tool: $tool; run nix develop ./flake" >&2; exit 127; }; done
yamllint gitops
schema_root="$PWD/schemas/kubernetes"
if [[ ! -d "$schema_root" ]]; then
  echo 'missing pinned repository CRD schemas under schemas/kubernetes' >&2
  exit 69
fi
while IFS= read -r -d '' file; do
  case "$file" in
    gitops/secrets/*) continue ;;
  esac
  output=$(kubectl kustomize "$(dirname "$file")" | kubeconform -strict -summary -ignore-missing-schemas -skip CustomResourceDefinition -schema-location default -schema-location "$schema_root/{{.ResourceKind}}{{.KindSuffix}}.json" 2>&1)
  printf '%s\n' "$output"
  allow_skipped=false
  case "$file" in
    gitops/clusters/homelab-01/kustomization.yaml | \
      gitops/clusters/homelab-01/flux-system/kustomization.yaml | \
      gitops/ingress/crds/kustomization.yaml | \
      gitops/registry-cutover/components/flux-system/kustomization.yaml) allow_skipped=true ;;
  esac
  if grep -Eq 'Skipped: [1-9]' <<<"$output" && [[ $allow_skipped == false ]]; then
    echo 'missing Kubernetes schemas; refresh and commit the required CRD schemas' >&2
    exit 69
  fi
done < <(find gitops -name kustomization.yaml -print0 | sort -z)
