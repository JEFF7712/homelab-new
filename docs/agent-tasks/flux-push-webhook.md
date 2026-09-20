# Backlog: push-triggered Flux sync via GitLab webhook

Status: live verification in progress 2026-09-20 (this push is the end-to-end test).

## Problem

Flux sync is purely pull based (`gitops/clusters/homelab-01/flux-system/gotk-sync.yaml`):
GitRepository polls `main` every 1m, the flux-system Kustomization reconciles
every 10m. A `git push` can sit up to ~10 minutes before it is applied. No
Receiver/Notification resources exist (only the CRDs).

## Plan

1. Add `Receiver/gitlab-push` in namespace `flux-system` (notification
   v1beta3, type `gitlab`, events `["ping", "push"]`), reconciling
   GitRepository/flux-system and Kustomization/flux-system. Full manifest
   sketched in session 2026-09-18.
2. Create SOPS-encrypted Secret `receiver-token` in `flux-system` with a
   random token; reuse the value in GitLab.
3. Expose notification-controller (`/hook/<id>`, svc port 80) publicly via
   the Cloudflare tunnel (or Gateway API), e.g.
   `https://flux-webhook.<domain>/hook/<id>`, non-guessable hostname.
4. Add GitLab repo webhook: push events only, secret token, Test Push and
   confirm reconcile takes seconds.

## Implementation (2026-09-19)

- `gitops/flux-webhook/receiver.yaml`: `Receiver/gitlab-push` (flux-system,
  type `gitlab`, events `["ping", "push"]`), reconciling
  GitRepository/flux-system and Kustomization/flux-system via
  `secretRef: receiver-token`.
- `gitops/flux-webhook/receiver-token.yaml`: ExternalSecret syncing
  `receiver-token` (key `token`) from GitLab variable `FLUX_RECEIVER_TOKEN`
  via the `gitlab-project` ClusterSecretStore. Token via ESO rather than
  SOPS: flux-system bootstrap has no SOPS decryption stanza and reconciles
  before secrets/eso exist.
- `gitops/clusters/homelab-01/flux-webhook.yaml` + kustomization entry:
  cluster Kustomization over `./gitops/flux-webhook`, `dependsOn: eso`.
- `schemas/kubernetes/receiver-notification-v1.json`: pinned Receiver schema
  extracted from the vendored Flux v2.9.0 CRDs so `scripts/checks/gitops.sh`
  validates with zero skips.
- `tests/test_flux_webhook.py`: contract test for the above.

## Remaining live steps (need explicit go-ahead + LAN access)

1. Create GitLab CI variable `FLUX_RECEIVER_TOKEN` with a random token value.
2. Add tunnel ingress hostname (e.g. `flux-webhook.<domain>`) above the
   catch-all, origin `http://webhook-receiver.flux-system:80`.
3. Add GitLab repo webhook for push events only, secret token = same value.
   `kubectl -n flux-system get receiver gitlab-push` shows the `/hook/<id>`
   path after reconcile. Test Push and confirm reconcile takes seconds.

## Notes

- Touches shared infra (ingress hostname, secret, flux-system). Needs
  explicit go-ahead plus LAN access to apply and verify.
- Receiver only reconciles the two listed resources; downstream Kustomizations
  cascade normally.
