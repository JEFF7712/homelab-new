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

## CI runner lanes

`nas-privileged` is the protected NAS runner for deployment, OPNsense, and
registry import jobs. Its GitLab runner must be locked, protected, limited to
one job, and configured not to accept untagged jobs. Scope `SSH_DEPLOY_KEY`,
`HOSTS_KNOWN`, OPNsense, and registry credentials to the `production`
environment in GitLab.

`nas-ci` is a separate, one-job NAS runner for formatting, repository tests,
YAML/schema checks, secret scanning, and registry-lock validation on `main`
and release tags. Register it with the `nas-ci` tag, protected, locked, and
with untagged jobs disabled. Its authentication-token file is
`/persist/gitlab-runner/ci-authentication-token`; do not give it deployment,
OPNsense, or registry credentials. Feature branch and merge-request variants
remain untagged for the shared or separately isolated builder lane.
