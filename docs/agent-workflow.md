# Agent Workflow Operator Guide

The shared CLI is `python -m scripts.agent`; `just` provides stable recipes. Startup and offline checks do not contact infrastructure or decrypt secrets.

## Commands

- `just agent-context [--json] [--task ID]`: bounded startup packet. `AGENT_TASK_ID` is a session-scoped alternative. Without either, active tasks are listed and none is selected.
- `just doctor [--json]`: local tools, paths, nested flake, adapters, and credential references. It never reads credential values.
- `just check-changed [BASE] [--json] [--select-only]`: includes staged, unstaged, renamed, deleted, untracked, and merge-base changes, explains routing, and executes selected checks unless `--select-only` is used.
- `just check`: full offline validation. Run `just provision-check-deps` once when pinned provider or schema caches are absent.
- `just fmt` and `just fmt-check`: apply or verify repository formatting.
- `just task-new ID [--json]`: read creation JSON from stdin and refuse overwrite.
- `just task-resume ID [--json]`: report HEAD and fingerprint drift, stale verification, and the next action.
- `just task-checkpoint ID [--json]`: read a complete record plus `expected_revision` from stdin and atomically replace it under a per-task lock.
- `just task-export ID [--replace]`: write a sanitized Markdown handoff under `docs/agent-tasks/`.
- `just status cluster|network [--json] [--timeout SECONDS] [--record]`: bounded read-only live diagnostics. Cluster status reads node readiness, Flux reconciliation, and failed workloads through the current kubectl context. Network status pings configured cluster nodes and reports BGP unavailable unless read-only OPNsense credentials can be used. The default total budget is 30 seconds. `--record` writes sanitized, timestamped evidence under `.agent-state/evidence/`. These commands are never part of startup or offline checks.

## Task schema

Task IDs match `^[a-z0-9][a-z0-9._-]{0,63}$`, excluding `.` and `..`. Records use schema version 1 and contain objective, status, acceptance criteria, owner and session, owned files, base and checkpoint identity, decisions, completed and remaining work, failures, next action, and verification records. Status is `active`, `blocked`, or `complete`. Blocked records need a concrete dependency. Complete records need evidence for every satisfied criterion and no unresolved failures.

Verification records contain command, exit code, time, source fingerprint, evidence path, and stale state. Resume derives staleness without rewriting the record. Task records and runtime evidence live in ignored `.agent-state/` and remain checkout-local.

## Check mapping

Host Nix evaluates the affected host. Shared Nix evaluates all hosts. Reconciler Python runs Ruff, Pyright, and behavior tests. GitOps renders Kustomize boundaries and validates schemas. OpenTofu formats, initializes with its backend disabled, and validates. Workflow, CI, flake input, and unknown code changes select the full gate. Documentation selects link, reference, and whitespace checks.

The GitOps gate fails when a custom-resource schema is missing. `just provision-check-deps` snapshots the served CRD schemas from the configured cluster into ignored `.agent-cache/schemas/`; subsequent validation uses that local cache. It skips encrypted SOPS manifests, whose kind is ciphertext until Flux decrypts them, and the vendored CRD definitions themselves. Live probes are reported separately from repository validation.

## Transfer and cleanup

Exports omit raw task logs and redact common secrets and credential paths. An export does not contain an uncommitted patch. Transfer the commits or create a reviewed patch separately. Remove obsolete local task and evidence directories only after inspecting them; no command automatically deletes task state.

## JSON envelope

Structured commands return `schema_version`, `command`, and command-specific data. Failures return nonzero with `status: error`, `error_type`, and a sanitized `message`. Doctor items use `pass`, `fail`, or `unavailable`. Runtime evidence is timestamped and describes one observation, never perpetual health.
