# Agent Workflow Implementation Design

Date: 2026-09-05

## Scope

This design adapts `docs/agent-workflow-spec.md` to the current repository. The implementation provides a small local context packet, durable checkout-local task records, targeted and full validation, shared lifecycle hooks, local diagnostics, and explicit read-only live status commands. It does not publish changes, deploy infrastructure, modify `/home/rupan/nixos`, or write personal agent memory.

Existing infrastructure ownership remains unchanged. Existing untracked client configuration and documentation are user-owned and must be preserved. The implementation may extend those files only after inspecting their current contents and only where the workflow specification requires it.

## Architecture

A shared typed Python CLI under `scripts/agent/` owns structured behavior. Focused modules handle repository discovery and fingerprints, task persistence, context rendering, check selection and execution, doctor checks, evidence, live status, and command-line serialization. One CLI entrypoint exposes concise text output and stable JSON output.

The `justfile` provides the supported human and agent command interface. Hooks are thin, time-bounded adapters that normalize client payloads and invoke the shared CLI. Client configuration points to those adapters without duplicating business logic.

State lives under ignored `.agent-state/`. Each task has its own directory, versioned JSON record, lock, and evidence references. Atomic replacement preserves the last valid checkpoint. Task selection is explicit through a command argument or a session-scoped identifier. No repository-global active-task pointer is introduced.

## Delivery Stages

### Foundation

Create `AGENT_MAP.md`, the Python package and CLI entrypoint, stable `just` recipes, required development dependencies, and `.agent-state/` ignore rules. Implement safe task IDs, versioned records, atomic persistence, per-task locking, Git identity, dirty-state fingerprints, and the first behavior tests.

### Context and Verification

Implement bounded startup context, task resume and sanitized export, changed-path collection, check selection, check execution, and full offline validation. Git parsing covers staged, unstaged, deleted, renamed, committed-since-base, and nonignored untracked paths, including unusual filename characters. CI invokes the same entrypoints used locally.

### Integration

Implement shared hooks after inspecting installed Claude, Codex, and Cursor capabilities. Add doctor checks, sanitized evidence capture, and bounded cluster and network diagnostics that discover targets from repository configuration. Unsupported events and unavailable credentials produce explicit fallback or unavailable results.

### Acceptance

Use temporary Git repositories and synthetic fixtures to test recovery, concurrency, invalid input, stale verification, secret redaction, output bounds, timeouts, and check routing. Run the complete offline suite, smoke-test supported client adapters, measure startup output size and warm runtime, and inspect the final diff. Live checks remain separately reported observations.

## Interfaces and Data Flow

The CLI parses a command and resolves the repository root without network access. Read-only commands build structured result objects, then serialize them as concise text or JSON. Mutating task commands validate all input before acquiring the task lock and atomically replacing the record. Validation commands first collect Git paths, map each path to checks with reasons, then invoke the named repository entrypoints while preserving nonzero status.

Verification records bind a command and result to HEAD plus the dirty-state fingerprint. Resume recomputes both values and marks previous verification stale when either changes. Export reads an existing valid record, redacts secret-like values and machine credential paths, and writes reviewed Markdown metadata plus instructions for recovering uncommitted work.

Live status commands resolve configured targets before probing them, print the selected targets, apply per-probe and total timeouts, sanitize results, and optionally persist timestamped evidence. They never run during startup or offline validation.

## Error Handling

CLI failures use stable nonzero exits and actionable messages. Invalid task IDs, missing bases, lock conflicts, malformed checkpoint input, missing tools, unavailable targets, and timeouts are distinct results in JSON. Optional startup integrations fail open. Required checks fail when dependencies are absent. Existing valid task state remains readable after invalid input or interrupted writes.

Hooks prevent recursive invocation, enforce their own timeout, and avoid blocking startup when context generation fails. Validation hooks retain the originating command's failure status and store only sanitized check identity, exit status, and evidence location.

## Verification Strategy

Behavior tests exercise public commands rather than matching documentation strings. Temporary repositories cover dirty-state and Git path edge cases. Unit tests cover schema validation, fingerprint stability, redaction, task locking, atomic writes, selection rules, and JSON contracts. Integration tests verify that `just` recipes launch their intended checks and that client fixtures produce valid adapter responses.

The full offline check is a maintained superset of targeted checks. Nix formatting, host evaluation, Python lint and type checks, GitOps rendering and schema checks, OpenTofu formatting and offline validation, documentation checks, secret scanning, and workflow tests remain explicit commands. Network-dependent provisioning is separate from repeatable offline validation.

## Repository Boundaries

The implementation changes only this checkout. It preserves the modified `docs/network/switch-port-map.md`, the existing commit ahead of `origin/main`, and unrelated untracked files. Commits remain small and task-scoped. No hook auto-stages edits, and any Nix-required staging names only the files owned by this task.
