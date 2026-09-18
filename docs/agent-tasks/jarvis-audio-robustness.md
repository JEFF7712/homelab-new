# Agent Task: jarvis-audio-robustness

Status: `complete`

Base commit: `1898d489b42eab6c06d2ebbf12a3bfa3afd51d77`

Checkpoint HEAD: `1898d489b42eab6c06d2ebbf12a3bfa3afd51d77`

Owner: `Antigravity`

Session: `295fb00e-a526-4682-b862-8e83b1b1826a`

Exported at: `2026-09-18T14:54:40.735870+00:00`

Current HEAD at export: `81e84749cca36fb33c063bdcd245dfe470caf8f0`

## Objective

Make Jarvis audio resilient against soundbar input switching and ensure HyperX QuadCast is always the microphone input

## Acceptance criteria

- [x] WirePlumber declarative configuration assigns highest priority to HyperX QuadCast microphone and soundbar HDMI output, while deprioritizing onboard mic and QuadCast headphone jack (Configured in flake/hosts/homelab-05/default.nix and verified via nix eval)
- [x] Continuous HDMI clock watcher daemon runs on homelab-05 to automatically re-enable HDMI-A-2 when soundbar input changes and reconnects (satellite-hdmi-audio-clock updated to Type=simple with continuous loop in flake/hosts/homelab-05/default.nix)
- [x] Satellite deployment uses resilient substring matching for HyperX QuadCast (AUDIO_INPUT_DEVICE set to QuadCast in gitops/voice/satellite.yaml and validated with yamllint and gitops.sh)
- [x] All validation gates (check-changed, tests, yamllint, etc.) pass (check-changed passed cleanly with 0 exit code across docs, nix-host-homelab-05, and gitops)

## Owned source

- `flake/hosts/homelab-05/default.nix`
- `gitops/voice/satellite.yaml`
- `docs/runbooks/jarvis-voice.md`

## Remaining work

- None

## Verification

- None recorded

## Next action

Review git diff and present changes to user

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
