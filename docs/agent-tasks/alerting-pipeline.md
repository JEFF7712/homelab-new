# Agent Task: alerting-pipeline

Status: `complete`

Base commit: `ca9e591441a1d272bdc50a1a768c1f93fa20f336`

Checkpoint HEAD: `a257b4938f349c3d07608ec77f1f4c2e42ba75f3`

Owner: `Antigravity`

Session: `01d526cd-73c1-4dbd-8888-11bb5cdda981`

Exported at: `2026-09-16T03:57:26.357977+00:00`

Current HEAD at export: `a257b4938f349c3d07608ec77f1f4c2e42ba75f3`

## Objective

Fix Alertmanager notification delivery to ntfy and establish comprehensive homelab alerting rules

## Acceptance criteria

- [x] Alertmanager authenticates to ntfy using Bearer token without 403 errors (alertmanager_notifications_total{integration="webhook"} incremented with 0 failures; ntfy homelab-alerts received formatted alerts)
- [x] K3s phantom metrics targets (controller-manager, scheduler, proxy, etcd) are disabled in HelmRelease (Disabled in kube-prometheus-stack release.yaml values; false positive rules no longer present)
- [x] Prometheus rules for cluster health, workloads, GitOps, and GPUs are declared in GitOps (cluster-rules.yaml and gpu-rules.yaml created, added to kustomization.yaml, and applied)
- [x] Validation passes via just check-changed and yaml linting (just check-changed exit 0 with all 31 Kustomize overlays valid; just fmt-check exit 0)

## Owned source

- `gitops/observability/kustomization.yaml`
- `gitops/observability/kube-prometheus-stack/release.yaml`
- `gitops/observability/kube-prometheus-stack/secret.yaml`
- `gitops/observability/kube-prometheus-stack/cluster-rules.yaml`
- `gitops/observability/kube-prometheus-stack/gpu-rules.yaml`

## Remaining work

- None

## Verification

- None recorded

## Next action

Export task and review diff

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
