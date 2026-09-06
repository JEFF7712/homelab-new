#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
command -v tofu >/dev/null || { echo 'missing required tool: tofu; run nix develop ./flake' >&2; exit 127; }
tofu -chdir=tofu/opnsense fmt -check
if [[ ! -d tofu/opnsense/.terraform/providers ]]; then echo 'OpenTofu providers are not provisioned; run just provision-check-deps' >&2; exit 69; fi
TF_REGISTRY_CLIENT_TIMEOUT=1 tofu -chdir=tofu/opnsense init -backend=false -get=false -lockfile=readonly >/dev/null
tofu -chdir=tofu/opnsense validate
