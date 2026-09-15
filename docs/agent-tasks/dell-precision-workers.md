# Agent Task: dell-precision-workers

Status: `active`

Base commit: `c2d779f1046d19751659b08c657e55c55afcd023`

Checkpoint HEAD: `c2d779f1046d19751659b08c657e55c55afcd023`

Owner: `antigravity`

Session: `dell-precision-workers`

Exported at: `2026-09-15T22:29:48.308120+00:00`

Current HEAD at export: `c2d779f1046d19751659b08c657e55c55afcd023`

## Objective

Add Dell Precision 3460 SFF workstations (homelab-04 and homelab-05) as k3s GPU workers to NixOS flake

## Acceptance criteria

- [x] homelab.k3s module supports role = agent without breaking existing server configurations (All 10 hosts evaluated without error in scripts/checks/nix.sh all)
- [x] homelab-04 and homelab-05 evaluate cleanly in nix flake check (nix eval and nix flake check succeeded without errors)
- [x] NVIDIA GPU and container toolkit are enabled on worker nodes (flake/modules/nvidia.nix configured with proprietary driver (open = false for TU117), CDI generator, and Intel media drivers)
- [x] All offline repository checks pass (just check and just fmt-check completed with exit code 0)

## Owned source

- `flake/flake.nix`
- `flake/modules/k3s-server.nix`
- `flake/modules/nvidia.nix`
- `flake/hosts/homelab-04/default.nix`
- `flake/hosts/homelab-04/disk-config.nix`
- `flake/hosts/homelab-04/hardware-configuration.nix`
- `flake/hosts/homelab-05/default.nix`
- `flake/hosts/homelab-05/disk-config.nix`
- `flake/hosts/homelab-05/hardware-configuration.nix`
- `scripts/checks/nix.sh`
- `HARDWARE.md`

## Remaining work

- None

## Verification

- None recorded

## Next action

Ready for user review

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
