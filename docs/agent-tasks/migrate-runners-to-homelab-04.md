# Agent Task: migrate-runners-to-homelab-04

Status: `complete`

Base commit: `08d827cf4d11c9448ea2fe7a665b44351ac80632`

Checkpoint HEAD: `718c0115ba1325b86fc16c3eb95d2c42c55b82d2`

Owner: `antigravity`

Session: `migrate-runners-to-homelab-04`

Exported at: `2026-09-15T23:40:43.369982+00:00`

Current HEAD at export: `718c0115ba1325b86fc16c3eb95d2c42c55b82d2`

## Objective

Migrate GitHub Actions and GitLab CI runners from nas-01 to homelab-04

## Acceptance criteria

- [x] GitLab runner and GitHub Actions runner configurations are migrated from nas-01 to homelab-04 (flake/modules/gitlab-runner.nix created, imported in homelab-04, removed from nas-data.nix; github-runner-nixos.nix imported in homelab-04 and removed from nas-01; adguard firewall updated to permit SSH from homelab-04)
- [x] All Nix flake hosts evaluate cleanly with scripts/checks/nix.sh (just check-nix homelab-04, nas-01, and adguard-netbird-01 exited 0; just fmt-check passed)
- [x] Runner authentication tokens are provisioned on homelab-04 and services run cleanly (Tokens copied to /persist on homelab-04; nixos-rebuild switch activated github-runner-nixos-ci-1, github-runner-nixos-ci-2, and gitlab-runner online and listening for jobs; nas-01 rebuilt with runners removed)

## Owned source

- `flake/modules/github-runner-nixos.nix`
- `flake/modules/gitlab-runner.nix`
- `flake/modules/nas-data.nix`
- `flake/hosts/nas-01/default.nix`
- `flake/hosts/homelab-04/default.nix`
- `flake/modules/adguard-netbird-appliance.nix`

## Remaining work

- None

## Verification

- None recorded

## Next action

Ready for user verification and review

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
