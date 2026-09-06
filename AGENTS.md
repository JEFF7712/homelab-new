# Repository Guidelines

## Agent Operating Contract

Complete authorized work through verification. Inspect `git status`, applicable instructions, and affected code first. Preserve unrelated changes. Define observable acceptance criteria before editing; plan only multistep work. Resolve routine choices autonomously. Explain material architecture tradeoffs before implementation. Obtain authorization before publishing or changing shared infrastructure.

## Workflow Entry Points

Start with `just agent-context`, then use `AGENT_MAP.md` to find the owning source. Resume explicit task state with `just task-resume <id>`. Use `just check-changed` for scoped validation, `just check` for the full offline gate, and `just fmt-check` before handoff. Run live diagnostics explicitly with `just status cluster` or `just status network`.

Task records and evidence under `.agent-state/` are local and ignored. Export reviewed handoffs with `just task-export <id>` and transfer uncommitted patches separately. Do not auto-stage files. Full command contracts and schemas are in `docs/agent-workflow.md`.

## Context and Ownership

Read narrowly: start with `README.md`, then affected modules, tests, and runbooks. Treat plans as intent, source as implementation, and fresh observations as runtime evidence.

- `flake/`: hosts, reusable modules, disks, networking, k3s.
- `tofu/opnsense/`: provider-supported firewall resources.
- `opnsense_reconciler/`: inventory and settings outside provider coverage.
- `gitops/`: Kubernetes desired state, owned by Flux.
- `tests/`: checks; `docs/`: architecture and runbooks.
- `secrets/`: encrypted material; `HARDWARE.md`: hardware inventory only.

Give each resource one authoritative owner. Fix the owning source. Put specialized instructions near their subsystem; keep this file small and avoid duplicating documentation.

## Implementation Standards

Prefer explicit interfaces, cohesive modules, and deterministic behavior. Separate pure reconciliation decisions from I/O. Make mutations idempotent, validate before writes, and report actionable failures. Avoid speculative abstractions and compatibility layers without callers.

Use `nixfmt`, two-space YAML indentation, and typed Python with four-space indentation. Prefer automated enforcement over prose rules. Update affected documentation with behavior changes.

## Verification Contract

Use the pinned environment. From the repository root:

```sh
nix develop ./flake
python -m unittest discover -s tests -v
nix flake check ./flake
yamllint .
gitleaks detect --source . --redact
```

Format changed Nix files with `nixfmt`. Test observable behavior and failure paths in `test_*.py` files. Add meaningful regression tests for bugs. Prefer evaluated configuration and rendered manifests over source-string assertions. Keep routine tests offline and credential-free. Match verification to risk; static success does not prove deployment. Report missing checks explicitly.

## Collaboration and Completion

When delegating, assign disjoint file ownership and acceptance criteria; integrate serially and verify combined results. Keep commits atomic with imperative, scoped subjects. Never bypass hooks. Review the final diff for accidental changes and secrets.

Handoffs and merge requests state changes, verification results, and limitations. Verify delegated work independently.

## Infrastructure Changes

Keep secrets SOPS-encrypted and preserve TLS verification. Before deployment, verify target identity, review the plan, and identify recovery. Use CI for OpenTofu and OPNsense changes and Flux for Kubernetes. Verify live state after authorized deployment.
