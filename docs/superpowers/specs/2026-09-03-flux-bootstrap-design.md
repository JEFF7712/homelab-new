# Flux Bootstrap Design

## Status

Draft for review on 2026-09-03. Stops before storage classes (NAS NFS pending).

## Goal

Reconcile Kubernetes platform state from Git with Flux, starting from ESO so later
layers (storage, ingress, apps) can consume GitLab-backed secrets.

## Control plane

`flux bootstrap gitlab` runs once from the laptop against project `85910419`,
path `gitops/clusters/homelab-01`, with `--deploy-token-auth` (read-only Git transport).
A one-time Maintainer project token creates the deploy credential and is revoked
right after; it never enters Git, SOPS, or CI variables. Cilium stays owned by the
k3s Helm controller bootstrap chart; Flux must not manage the `cilium` HelmRelease.

## Layers (strict dependsOn order)

1. `flux-system`: bootstrap-managed source + sync. No hand edits.
2. `platform`: namespaces and the ESO `HelmRelease` (pinned chart version,
   chart-managed CRDs). No app workloads.
3. `secrets`: SOPS-encrypted bootstrap Secrets only, starting with the ESO GitLab
   API token. Flux decrypts with the `sops-age` secret in `flux-system`, created
   out of band. Plaintext secrets never enter Git.
4. `eso`: one namespace-local `SecretStore` per consuming namespace (blast-radius
   rule, no `ClusterSecretStore`), then `ExternalSecret` objects with explicit
   `data` mappings, `target.creationPolicy: Owner`, `refreshInterval: 1h`.
5. `apps`: gated on the ESO layer, health-checked. Not built in this design;
   storage classes and ingress wait for NAS NFS.

## Secrets and tokens

- Age key: generated locally, private key in ignored `secrets/keys/`, public
  recipient in `.sops.yaml`. One recipient only until the NAS runner exists.
- ESO GitLab token: project access token, `api` scope, 1-year expiry, committed
  only as SOPS ciphertext. Separate token per trust domain later.
- Canary variable: `FLUX_ESO_CANARY` project variable proves the full chain
  (GitLab -> store -> secret) without touching real credentials.

## Acceptance

- `flux check` passes; `GitRepository` and all four Kustomizations Ready.
- `kubectl -n default get externalsecret eso-canary` reports Synced; the output
  Secret matches the canary variable hash.
- `gitleaks` clean; no plaintext token material in Git.
- Deleting the canary `ExternalSecret` from Git prunes the output Secret.
