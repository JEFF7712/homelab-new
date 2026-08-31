# homelab-new

NixOS homelab desired state.

## Ownership

- `flake/` owns NixOS hosts, disks, host networking, k3s installation, and host secrets.
- `tofu/` owns API-managed external systems and supported OPNsense resources.
- `opnsense-reconciler/` owns OPNsense interface and FRR settings absent from the OpenTofu provider.
- `gitops/` owns all Kubernetes objects through Flux.
- `secrets/` contains only SOPS-encrypted material.

## Deployment

First installation uses `nixos-anywhere`. Subsequent NixOS activation uses `deploy-rs` from the NAS-hosted GitLab runner. OpenTofu applies and OPNsense reconciliation run only in CI. Flux reconciles Kubernetes state from Git.

Do not apply infrastructure from a laptop.
