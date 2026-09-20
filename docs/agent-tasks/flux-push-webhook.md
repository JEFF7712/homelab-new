# Backlog: push-triggered Flux sync via GitLab webhook

Status: live and verified 2026-09-20. Push `ce04669` handled 1s after push, applied cluster-wide within 9s (was up to ~10m on polls).

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
  type `gitlab`, events `["Push Hook", "Tag Push Hook"]`), reconciling
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

## Verification (2026-09-20)

- `Receiver/gitlab-push` Ready, webhook path `/hook/8b8f...` (see `kubectl -n
  flux-system get receiver gitlab-push -o jsonpath='{.status.webhookPath}'`).
- Tunnel `homelab` v73: `flux-wh-33b0c8004348.rupan.dev ->
  http://webhook-receiver.flux-system:80`, DNS CNAME to the tunnel,
  Access Bypass app `flux-webhook-bypass` (wildcard app would 302 to login).
- GitLab project webhook id `89560154`: push events only, SSL verification
  on. Token in project variable `FLUX_RECEIVER_TOKEN` (masked).
- Gotcha fixed during rollout: Receiver `events` must use GitLab-native
  names (`Push Hook`, `Tag Push Hook`); generic `push` is rejected with
  `the GitLab event "Push Hook" is not authorised`.
- End-to-end: push `ce04669` at 03:45:01Z, notification-controller log
  `handling GitLab event: Push Hook` at 03:45:02, new revision fetched and
  applied by 03:45:10.

## Remaining live steps

None. All completed 2026-09-20:

1. ~~Create GitLab CI variable `FLUX_RECEIVER_TOKEN`~~ done (masked).
2. ~~Add tunnel ingress hostname~~ done, see Verification.
3. ~~Add GitLab repo webhook~~ done (id `89560154`).
   `kubectl -n flux-system get receiver gitlab-push` shows the `/hook/<id>`
   path. Test Push verified: reconcile in seconds.

## Notes

- Touches shared infra (ingress hostname, secret, flux-system). Needs
  explicit go-ahead plus LAN access to apply and verify.
- Receiver only reconciles the two listed resources; downstream Kustomizations
  cascade normally.
