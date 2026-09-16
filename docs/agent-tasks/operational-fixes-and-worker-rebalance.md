# Agent Task: operational-fixes-and-worker-rebalance

Status: `complete`

Base commit: `492473fd0a546902f649f97dfaf056b35724691d`

Checkpoint HEAD: `492473fd0a546902f649f97dfaf056b35724691d`

Owner: `Antigravity`

Session: `ses_operational_fixes`

Exported at: `2026-09-16T18:44:26.023361+00:00`

Current HEAD at export: `492473fd0a546902f649f97dfaf056b35724691d`

## Objective

Perform operational fixes for Immich backups and NAS ZFS memory alerting, clean duplicate NVIDIA plugin, rebalance GitHub runners, and restore clean CI checks

## Acceptance criteria

- [x] Immich library local backup job succeeds without permission denied errors on .storage (Updated gitops/backups/library-local.yaml to exclude /library/.storage, set --host immich, and call restic unlock. Verified test backup succeeded processing 46.182 GiB and saving snapshot 88ea8ef3 cleanly. Cleared failed jobs from cluster.)
- [x] Prometheus NodeHighMemoryUsage alert accounts for ZFS ARC cache on nas-01 (Updated NodeHighMemoryUsage alert expr in gitops/observability/kube-prometheus-stack/cluster-rules.yaml to subtract node_zfs_arc_size. Verified live query evaluates nas-01 real memory at ~17% and alert resolved in Alertmanager.)
- [x] Duplicate nvidia-device-plugin-daemonset is removed from kube-system and homelab-05 legacy label cleaned up (Deleted duplicate DaemonSet nvidia-device-plugin-daemonset from kube-system and removed pci.nvidia.com/gpu label from homelab-05. Verified GitOps-managed nvidia-device-plugin is running 1/1 on homelab-04 and 1/1 on homelab-05.)
- [x] GitHub Actions runner deployments are rebalanced across homelab-04 and homelab-05 (Triggered rollout restart of all 13 runner deployments. Runners rescheduled to homelab-05, balancing memory and CPU requests evenly across worker nodes (homelab-04: 11% CPU / 41% RAM, homelab-05: 25% CPU / 24% RAM; actual usage ~3-7% CPU and 9-12% RAM).)
- [x] morning_weather_briefing.yaml line length fixed and just check passes cleanly (Wrapped value_template in morning_weather_briefing.yaml. just check-changed and just fmt-check pass with exit code 0.)

## Owned source

- `gitops/backups/library-local.yaml`
- `gitops/observability/kube-prometheus-stack/cluster-rules.yaml`
- `gitops/automation/github-runner/deployment.yaml`
- `home-assistant/automations/morning_weather_briefing.yaml`

## Remaining work

- None

## Verification

- None recorded

## Next action

Export task and present summary to user

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
