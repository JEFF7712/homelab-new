# Repository Agent Guide

Start with `just agent-context`, then use `AGENT_MAP.md` to find the owning source. Resume explicit task state with `just task-resume <id>`. Do not infer deployment or live health from repository checks.

Use `just check-changed` for scoped work and `just check` for the full offline gate. Run `just fmt-check` before handoff. Live diagnostics are explicit: `just status cluster` and `just status network`.

Preserve infrastructure ownership: `flake/` owns hosts, `gitops/` owns Kubernetes state, `tofu/opnsense/` owns provider-supported firewall resources, and `opnsense_reconciler/` owns unsupported settings. Do not deploy from a laptop. Do not auto-stage files; stage only task-owned paths when needed for Nix evaluation.

Task records and evidence under `.agent-state/` are local and ignored. Export reviewed handoffs with `just task-export <id>`; transfer uncommitted patches separately. Full contracts and schemas are in `docs/agent-workflow.md`.
