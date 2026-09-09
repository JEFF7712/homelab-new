# Agent Map

Use this map to find the authoritative source before editing. The validation entries are the minimum checks currently available. Infrastructure deployment and live probes remain separate, authorized operations.

| Area | Inspect and edit | Minimum validation | Runbooks and references |
| --- | --- | --- | --- |
| Host configuration and networking | `flake/hosts/<host>/default.nix` | `nix flake check ./flake` | `docs/network/switch-port-map.md` |
| Host storage | `flake/hosts/<host>/disk-config.nix`; `flake/hosts/nas-01/tank-config.nix` | `nix flake check ./flake` | `docs/superpowers/plans/2026-09-01-nas-base-installation.md` |
| Shared NixOS modules | `flake/modules/` and their consumers under `flake/hosts/` | `nix flake check ./flake` | Relevant plan under `docs/superpowers/plans/` |
| k3s installation | `flake/modules/k3s-server.nix`; k3s hosts under `flake/hosts/` | `nix develop ./flake -c python -m unittest discover -s tests -v`; `nix flake check ./flake` | `docs/superpowers/plans/2026-08-31-k3s-control-plane.md` |
| Flux and Kubernetes workloads | `gitops/`; cluster entrypoint at `gitops/clusters/homelab-01/` | `nix develop ./flake -c yamllint .`; `nix develop ./flake -c python -m unittest discover -s tests -v` | `docs/superpowers/plans/2026-09-03-flux-bootstrap.md`; `docs/superpowers/plans/2026-09-03-nas-data-services.md` |
| OPNsense provider resources | `tofu/opnsense/` | `nix develop ./flake -c tofu -chdir=tofu/opnsense fmt -check`; CI performs initialized validation and plans | `docs/runbooks/opnsense-recovery.md`; `docs/runbooks/opnsense-bgp-proof.md` |
| OPNsense reconciliation | `opnsense_reconciler/`; behavior tests under `tests/test_opnsense_*.py` | `nix develop ./flake -c python -m unittest discover -s tests -v` | `docs/runbooks/opnsense-recovery.md`; `docs/runbooks/opnsense-bgp-proof.md` |
| Encrypted secrets | `.sops.yaml`; `gitops/secrets/`; encrypted secret manifests beside their consumers | `nix develop ./flake -c yamllint .`; `gitleaks detect --source . --redact` when `gitleaks` is available | `docs/superpowers/plans/2026-09-03-flux-bootstrap.md` |
| Agent tooling | `scripts/agent/`; `justfile`; `tests/test_agent_cli.py`; `.agent-state/` for ignored local state | `nix develop ./flake -c python -m unittest tests.test_agent_cli -v`; full suite with `nix develop ./flake -c python -m unittest discover -s tests -v` | `docs/superpowers/specs/2026-09-05-agent-workflow-design.md`; `docs/superpowers/plans/2026-09-05-agent-workflow.md` |
| Home Assistant configuration | `home-assistant/`; `scripts/home_assistant/`; `tests/test_home_assistant_*.py` | `nix develop ./flake -c bash scripts/checks/home-assistant.sh` | `docs/runbooks/home-assistant-configuration.md`; `docs/superpowers/plans/2026-09-09-home-assistant-configuration-adoption.md` |

The stable command surface is listed by `python -m scripts.agent --help` and the `justfile`. Use `just agent-context` for startup, `just check-changed` for targeted offline validation, `just doctor` for local readiness, and `just status cluster|network` for bounded read-only live diagnostics.
