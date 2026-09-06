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

The GitOps gate fails when a custom-resource schema is missing. Required CRD schemas are pinned under `schemas/kubernetes/`, so local and CI validation use the same offline inputs. `just refresh-crd-schemas` snapshots all served cluster schemas into ignored `.agent-cache/schemas/` for review when the pinned set needs updating. `just provision-check-deps` installs the locked OpenTofu provider before the offline gate. GitOps validation skips encrypted SOPS manifests, whose kind is ciphertext until Flux decrypts them, and the vendored CRD definitions themselves. Live probes are reported separately from repository validation.

## Transfer and cleanup

Exports omit raw task logs and redact common secrets and credential paths. An export does not contain an uncommitted patch. Transfer the commits or create a reviewed patch separately. Remove obsolete local task and evidence directories only after inspecting them; no command automatically deletes task state.

## JSON envelope

Structured commands return `schema_version`, `command`, and command-specific data. Failures return nonzero with `status: error`, `error_type`, and a sanitized `message`. Doctor items use `pass`, `fail`, or `unavailable`. Runtime evidence is timestamped and describes one observation, never perpetual health.

## Acceptance coverage

| Scenario | Executable proof |
| --- | --- |
| Only untracked files are dirty | `tests.test_agent_git_state.GitStateTest.test_only_untracked_files_are_dirty_and_change_the_fingerprint` |
| Zero, one, or multiple active tasks | `tests.test_agent_context.AgentContextTest.test_no_task_lists_active_tasks_without_selecting` and `test_explicit_and_session_task_selection` |
| Source edit makes verification stale | `tests.test_agent_tasks.TaskRecordTest.test_resume_reports_drift_unavailable_base_and_stale_verification_without_rewrite` |
| HEAD drift or unavailable base | `tests.test_agent_tasks.TaskRecordTest.test_resume_reports_drift_unavailable_base_and_stale_verification_without_rewrite` |
| Concurrent writers conflict | `tests.test_agent_tasks.TaskRecordTest.test_checkpoint_requires_matching_revision_and_preserves_previous_record` |
| Invalid or interrupted checkpoint preserves state | `tests.test_agent_tasks.TaskRecordTest.test_lock_conflict_and_interrupted_replace_keep_valid_record` |
| Spaces and unusual Git path bytes | `tests.test_agent_git_state.GitStateTest.test_collects_all_local_change_sources_with_unusual_paths` and `test_repository_root_with_newline_is_preserved` |
| Renamed, deleted, staged, and untracked files route | `tests.test_agent_git_state.GitStateTest.test_collects_all_local_change_sources_with_unusual_paths` and `test_staged_deletion_is_an_index_change` |
| Unknown or shared check paths select full validation | `tests.test_agent_checks.AgentCheckSelectionTest.test_routes_repository_surfaces_with_reasons` |
| Startup remains local without credentials | `tests.test_agent_context.AgentContextTest.test_text_output_is_bounded_and_reports_truncation` and `tests.test_agent_doctor.AgentDoctorTest.test_doctor_reports_structured_results_without_secret_values` |
| Missing required tooling fails explicitly | `nix develop ./flake -c python -m unittest tests.test_agent_doctor -v` |
| Live timeout is bounded and nonhealthy | `tests.test_agent_status.AgentStatusTest.test_unknown_probe_is_nonhealthy_and_bounded` |
| Secrets are removed from evidence and handoff | `tests.test_agent_status.AgentStatusTest.test_evidence_is_sanitized` and `tests.test_agent_context.AgentContextTest.test_export_redacts_and_explains_uncommitted_recovery` |
| Unsupported hook event has an explicit fallback | `tests.test_agent_hooks.AgentHookTest.test_client_hook_configuration_is_valid_json`; use `just agent-context` where a lifecycle event is unavailable |
| Export contains fresh-session recovery fields | `tests.test_agent_context.AgentContextTest.test_export_redacts_and_explains_uncommitted_recovery` |
