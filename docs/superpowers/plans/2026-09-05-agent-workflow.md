# Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the repository-local agent navigation, task continuity, validation, hooks, diagnostics, and evidence interface specified in `docs/agent-workflow-spec.md`.

**Architecture:** A typed Python package under `scripts/agent/` owns Git discovery, task records, check routing, diagnostics, redaction, and serialization. A single CLI entrypoint is exposed through `just`, while small shell hook adapters translate installed client events into that shared interface. Checkout-local state is atomic, locked per task, ignored by Git, and tested through temporary repositories.

**Tech Stack:** Python 3.13 standard library, `unittest`, Git, just, Bash, Nix flakes, Ruff, Pyright, yamllint, kubeconform, kubectl, Helm, OpenTofu, gitleaks.

---

## File Structure

- `AGENT_MAP.md`: verified task routing, owning paths, minimum validation, and runbooks.
- `justfile`: stable public recipes only; delegates structured behavior to the CLI and check scripts.
- `.gitignore`: ignores `.agent-state/` and generated offline dependency caches.
- `scripts/agent/__main__.py`: argument parser and exit-code boundary.
- `scripts/agent/models.py`: JSON-compatible typed result and task record models.
- `scripts/agent/git_state.py`: repository identity, robust Git path collection, and content fingerprints.
- `scripts/agent/tasks.py`: task ID validation, locking, atomic writes, checkpoint, resume, and export.
- `scripts/agent/context.py`: bounded startup packet and task selection.
- `scripts/agent/checks.py`: changed-path mapping, explanations, and check execution.
- `scripts/agent/doctor.py`: offline dependency, repository, flake, and adapter diagnosis.
- `scripts/agent/redact.py`: shared secret and credential-path sanitization.
- `scripts/agent/evidence.py`: versioned timestamped evidence persistence.
- `scripts/agent/status.py`: bounded read-only cluster and network probes.
- `scripts/checks/`: deterministic check entrypoints for Nix, Python, GitOps, OpenTofu, docs, and the full gate.
- `hooks/`: shared lifecycle adapters and payload normalization.
- `.claude/settings.json`, `.codex/config.toml`, and any discovered Cursor configuration: preserved client configuration extended only for supported events.
- `docs/agent-workflow.md`: schemas, command contracts, task lifecycle, hook support, provisioning, cleanup, and diagnostics.
- `docs/decisions/0001-agent-workflow-state.md`: consequential state and concurrency decision.
- `docs/agent-tasks/.gitkeep`: export destination without committing local task state.
- `tests/agent_helpers.py`: temporary Git repository and CLI fixtures.
- `tests/test_agent_git_state.py`: dirty state, bases, path parsing, and fingerprints.
- `tests/test_agent_tasks.py`: validation, atomicity, concurrency, drift, and export.
- `tests/test_agent_context.py`: task selection, bounds, truncation, and runtime behavior.
- `tests/test_agent_checks.py`: routing, reasons, deduplication, and execution failures.
- `tests/test_agent_doctor.py`: pass, fail, unavailable, and redaction behavior.
- `tests/test_agent_status.py`: target discovery, timeouts, JSON, and evidence behavior.
- `tests/test_agent_hooks.py`: payload fixtures, recursion guards, failure preservation, and fallbacks.
- `.gitlab-ci.yml`: uses the same offline `just` entrypoints as local validation.
- `flake/flake.nix`: adds `just`, ShellCheck, and any pinned offline render dependencies proven necessary.

## Milestone 1: Command and State Foundation

### Task 1: Add routing and public command skeleton

**Files:**
- Create: `AGENT_MAP.md`
- Create: `justfile`
- Modify: `.gitignore`
- Create: `scripts/__init__.py`
- Create: `scripts/agent/__init__.py`
- Create: `scripts/agent/__main__.py`
- Create: `tests/test_agent_cli.py`

- [ ] **Step 1: Write failing CLI contract tests**

Create tests that run `python -m scripts.agent --help`, assert every specified subcommand appears, run `context --json` in a temporary Git repository, and assert the result is a JSON object with `schema_version`, `command`, and `repository` keys. Assert unknown commands return exit status 2 without a traceback.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_cli -v`

Expected: failure because `scripts.agent` does not exist.

- [ ] **Step 3: Implement the CLI boundary and recipes**

Add argparse subcommands `context`, `doctor`, `check-changed`, `task-new`, `task-resume`, `task-checkpoint`, `task-export`, and `status`. Give structured commands a shared `--json` flag. Add `just` recipes named exactly `agent-context`, `doctor`, `check-changed`, `check`, `fmt`, `fmt-check`, `task-new`, `task-resume`, `task-checkpoint`, `task-export`, and `status`. Recipes invoke `python -m scripts.agent` or a named `scripts/checks/` entrypoint and preserve its exit code.

Add `.agent-state/` to `.gitignore`. Populate `AGENT_MAP.md` only with paths verified in the checkout, covering `flake/hosts`, `flake/modules`, `gitops`, `tofu/opnsense`, `opnsense_reconciler`, `secrets`, and agent tooling.

- [ ] **Step 4: Verify the public skeleton**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_cli -v`

Expected: all CLI contract tests pass.

- [ ] **Step 5: Commit the skeleton**

Stage only the files listed in this task and commit with `feat: add agent workflow command interface`.

### Task 2: Implement repository identity and dirty fingerprints

**Files:**
- Create: `scripts/agent/models.py`
- Create: `scripts/agent/git_state.py`
- Create: `tests/agent_helpers.py`
- Create: `tests/test_agent_git_state.py`

- [ ] **Step 1: Write failing Git-state tests**

Cover clean, staged, unstaged, deleted, renamed, and nonignored untracked files. Include filenames containing spaces, tabs, newlines, and leading dashes. Assert a repository containing only untracked files is dirty. Assert `.agent-state/` never contributes to the fingerprint. Assert an invalid base returns a typed error and causes no Git mutation.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_git_state -v`

Expected: import failure for `scripts.agent.git_state`.

- [ ] **Step 3: Implement NUL-safe Git discovery**

Use `git status --porcelain=v2 -z --untracked-files=all`, `git diff --name-status -z`, `git diff --cached --name-status -z`, and `git ls-files --others --exclude-standard -z`. When a base is supplied, resolve it with `git rev-parse --verify` and collect committed paths from `git diff --name-status -z "$(git merge-base "$base" HEAD)" HEAD` through argv, never shell interpolation.

Hash normalized path identity, change kind, index/worktree state, tracked blob or working-tree bytes, and nonignored untracked bytes with SHA-256. Do not store file contents. Return branch or detached state, HEAD, base availability, counts by state, changed paths, and fingerprint through typed dataclasses.

- [ ] **Step 4: Verify Git behavior**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_git_state -v`

Expected: all Git-state tests pass, including unusual names.

- [ ] **Step 5: Commit Git state support**

Stage the four task files and commit with `feat: fingerprint complete checkout state`.

### Task 3: Implement safe task records and checkpoints

**Files:**
- Create: `scripts/agent/tasks.py`
- Create: `scripts/agent/redact.py`
- Create: `tests/test_agent_tasks.py`
- Create: `docs/decisions/0001-agent-workflow-state.md`

- [ ] **Step 1: Write failing task lifecycle tests**

Test IDs against `^[a-z0-9][a-z0-9._-]{0,63}$`; reject `..`, separators, absolute paths, uppercase, empty IDs, and overlong IDs. Test create-without-overwrite, required record fields, checkpoint input from stdin, revision conflicts between two writers, lock timeout, invalid JSON, interrupted replacement, drift after an uncommitted edit, HEAD drift, unavailable base commit, stale verification, blocked dependency requirements, and refusal to mark incomplete acceptance criteria complete.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_tasks -v`

Expected: import failure for `scripts.agent.tasks`.

- [ ] **Step 3: Implement the task store**

Persist `.agent-state/tasks/<id>/task.json` with schema version 1, record revision, task metadata, acceptance criteria objects with satisfied flags and evidence, ownership boundaries, base and checkpoint identity, decisions, completed and remaining work, failures, next action, and verification records. Accept task creation metadata and checkpoint documents through JSON stdin so multiline values remain unambiguous.

Acquire `.agent-state/tasks/<id>/.lock` using atomic exclusive creation with owner PID, session, and timestamp. Require the caller's expected revision for updates. Write fully validated JSON to a same-directory temporary file, flush and `fsync`, then `os.replace` and `fsync` the directory. Remove only a lock owned by the current process. Preserve the previous record on every validation or write failure.

Write the decision record with problem, decision, rationale, rejected alternatives, consequences, and superseding-record semantics. Implement shared redaction for token-like values, authorization headers, private keys, secret environment assignments, and paths under known credential directories.

- [ ] **Step 4: Verify task safety**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_tasks -v`

Expected: all task lifecycle and failure-path tests pass.

- [ ] **Step 5: Commit task continuity**

Stage the task files and commit with `feat: add atomic agent task checkpoints`.

## Milestone 2: Context and Verification

### Task 4: Implement bounded context, resume, and export

**Files:**
- Create: `scripts/agent/context.py`
- Modify: `scripts/agent/tasks.py`
- Modify: `scripts/agent/__main__.py`
- Create: `tests/test_agent_context.py`
- Create: `docs/agent-tasks/.gitkeep`

- [ ] **Step 1: Write failing context and transfer tests**

Test no tasks, one task, and multiple tasks without implicit selection. Test explicit `--task` and session-scoped `AGENT_TASK_ID`. Assert another task is never selected as fallback. Assert text output is at most 6144 bytes, truncation is explicit, large changed-file sets report counts, JSON remains complete, no startup subprocess invokes Nix, kubectl, network tools, or secret decryption, and missing optional tools do not fail startup.

Test resume reports task owner, source paths, drift, stale verification, remaining work, and exact next action. Test export redacts synthetic secrets, includes evidence references and patch recovery instructions, rejects missing evidence, and never claims that uncommitted changes transfer across machines.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_context -v`

Expected: failures for missing context and export behavior.

- [ ] **Step 3: Implement bounded rendering and export**

Build the startup result from Git state and optional selected task. Render sections in priority order: repository identity, dirty summary, selected or available tasks, checkpoint drift, next action, relevant validation, and evidence references. Apply a byte-aware UTF-8 truncator at 6144 bytes that preserves a final truncation notice and detail paths.

Write sanitized handoffs atomically to `docs/agent-tasks/<id>.md`, refusing overwrite unless the existing export belongs to the same task and the command receives an explicit replacement flag documented in the operator guide.

- [ ] **Step 4: Verify context behavior and measure locally**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_context -v`

Run: `nix develop ./flake -c /usr/bin/time -f '%e seconds, %M KiB' just agent-context`

Expected: tests pass, output is at most 6144 bytes, and warm runtime is recorded for the final report.

- [ ] **Step 5: Commit context and transfer support**

Stage the listed files and commit with `feat: add bounded agent context and handoff`.

### Task 5: Implement changed-path check selection

**Files:**
- Create: `scripts/agent/checks.py`
- Modify: `scripts/agent/__main__.py`
- Create: `tests/test_agent_checks.py`

- [ ] **Step 1: Write failing selection tests**

Create table-driven tests for host Nix, shared Nix, reconciler Python, GitOps, OpenTofu, agent workflow, flake inputs, CI/check infrastructure, documentation-only, and unknown source paths. Assert reasons are present, checks deduplicate in stable order, shared modules select all hosts, invalid bases fail clearly, and `--json` reports collected paths, reasons, commands, execution results, and overall status.

Use temporary executable fixtures to prove selected checks actually run, retain nonzero exit codes, stop according to the documented execution policy, and reference detailed evidence without dumping unbounded logs.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_checks -v`

Expected: import failure for `scripts.agent.checks`.

- [ ] **Step 3: Implement maintained routing**

Represent routing as ordered path predicates returning named checks and human-readable reasons. Map unknown code, `flake/flake.lock`, `.gitlab-ci.yml`, `justfile`, `scripts/checks/`, and routing implementation changes to the full gate. Keep documentation-only checks limited to links, command references, and whitespace. Ensure the full gate declares every targeted check as a member.

Execute commands with argv lists from the repository root, capture bounded stdout and stderr to `.agent-state/evidence/checks/`, preserve exit status, and sanitize saved output. Selection-only JSON must be available without executing checks.

- [ ] **Step 4: Verify selection and execution**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_checks -v`

Expected: all routing and execution tests pass.

- [ ] **Step 5: Commit targeted selection**

Stage the listed files and commit with `feat: select checks from complete git state`.

### Task 6: Add deterministic check entrypoints and CI alignment

**Files:**
- Create: `scripts/checks/python.sh`
- Create: `scripts/checks/nix.sh`
- Create: `scripts/checks/gitops.sh`
- Create: `scripts/checks/tofu.sh`
- Create: `scripts/checks/docs.py`
- Create: `scripts/checks/whitespace.py`
- Create: `scripts/checks/agent-workflows.sh`
- Create: `scripts/checks/all.sh`
- Modify: `justfile`
- Modify: `flake/flake.nix`
- Modify: `.gitlab-ci.yml`
- Modify: `tests/test_flake_contract.py`
- Create: `tests/test_check_entrypoints.py`

- [ ] **Step 1: Write failing entrypoint tests**

Assert each public recipe invokes its real script and each script performs the intended tool invocation. Use fixture binaries at the front of `PATH` to record argv for Ruff, Pyright, nixfmt, Nix evaluation, yamllint, kustomize or Helm rendering, kubeconform, `tofu fmt`, `tofu init -backend=false`, `tofu validate`, and gitleaks. Assert a missing required binary fails with a concrete install remedy rather than skipping.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_check_entrypoints -v`

Expected: failures because check scripts do not exist.

- [ ] **Step 3: Implement offline checks**

Use strict Bash with explicit repository-root discovery and argv arrays. Python checks run Ruff format-check, Ruff lint, Pyright, and unittests. Nix checks run `nixfmt --check` for tracked Nix files, `nix flake check ./flake --no-write-lock-file`, and affected host evaluations. GitOps checks render the nearest committed Kustomize boundary, validate generated YAML with pinned local schemas, and fail when required chart or schema caches are absent. OpenTofu checks run format, initialize with `-backend=false`, and validate using provisioned provider data without contacting the backend.

Add separate `just provision-check-deps` for network-dependent initial schema, chart, and provider provisioning. `just check` must remain offline after provisioning and run agent workflow tests, Python, Nix, GitOps, OpenTofu, docs, whitespace, and gitleaks. Add `just fmt` and nonmutating `just fmt-check`.

Add `just`, `shellcheck`, and any required pinned render tools to the nested flake. Update GitLab jobs to call `just fmt-check`, `just check`, and the same focused scripts while leaving OPNsense plan/apply ownership and manual apply behavior intact.

- [ ] **Step 4: Run focused and full verification**

Run: `nix develop ./flake -c python -m unittest tests.test_check_entrypoints -v`

Run: `nix develop ./flake -c just fmt-check`

Run: `nix develop ./flake -c just check`

Expected: all pass offline with provisioned dependencies. If caches are not provisioned, the relevant check fails and prints the exact provisioning command; record that environmental blocker without weakening the check.

- [ ] **Step 5: Commit offline validation**

Stage only the files listed in this task and commit with `feat: align targeted checks with offline CI`.

## Milestone 3: Hooks, Doctor, and Diagnostics

### Task 7: Add doctor and operator documentation

**Files:**
- Create: `scripts/agent/doctor.py`
- Modify: `scripts/agent/__main__.py`
- Create: `tests/test_agent_doctor.py`
- Create: `docs/agent-workflow.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write failing doctor tests**

Test pass, fail, and unavailable outcomes for commands, expected paths, nested flake selection, adapter configuration, and credential references. Assert doctor makes no network calls, reads no credential values, prints no environment values, and gives a concrete remedy for every fail or unavailable result. Assert JSON includes timestamp, checks, status, and remedy fields.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_doctor -v`

Expected: import failure for `scripts.agent.doctor`.

- [ ] **Step 3: Implement doctor and exact documentation**

Inspect executable availability with `shutil.which`, repository paths with `pathlib`, nested flake identity through local file checks, client adapter configuration through parsers, and credential references only by variable or configured path presence. Never open credential files.

Document every command argument, JSON result schema, task input schema, task status rules, session selection, locking, cleanup, export, evidence retention, provisioning, check mapping, timeout, client support, and explicit fallback. Reduce `AGENTS.md` to compact entrypoints and rules while preserving existing project ownership guidance.

- [ ] **Step 4: Verify doctor and documentation**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_doctor -v`

Run: `nix develop ./flake -c just doctor`

Run: `nix develop ./flake -c python scripts/checks/docs.py`

Expected: tests and docs checks pass; environmental unavailable results are explicit and non-secret.

- [ ] **Step 5: Commit doctor and guide**

Stage the listed files and commit with `feat: add offline agent workflow doctor`.

### Task 8: Inspect and implement shared client hooks

**Files:**
- Create: `hooks/common.sh`
- Create: `hooks/session-start`
- Create: `hooks/validation-result`
- Create: `hooks/stop`
- Create: `tests/test_agent_hooks.py`
- Modify if supported: `.claude/settings.json`
- Modify if supported: `.codex/config.toml`
- Modify only if discovered: `.cursor/hooks.json`
- Modify: `docs/agent-workflow.md`

- [ ] **Step 1: Record installed client capabilities**

Run local version and help commands for installed `claude`, `codex`, and `agent` clients. Inspect existing configuration schemas or official local documentation. Record each supported event, payload source, timeout mechanism, and response contract in the operator guide. Mark absent clients and events unavailable. Do not invent configuration keys.

- [ ] **Step 2: Write failing payload tests**

Add sanitized fixtures for every confirmed client event. Assert session start invokes bounded context once and fails open, validation failure records only check identity, exit status, and evidence path while returning the original nonzero status, stop emits a bounded reminder only for stale or missing checkpoints or unresolved validation, recursion is blocked through an environment guard, and unsupported clients have an explicit command fallback.

- [ ] **Step 3: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_hooks -v`

Expected: failures because hooks are absent.

- [ ] **Step 4: Implement and wire confirmed adapters**

Put payload parsing, repository containment, timeout, recursion guard, task resolution, and response helpers in `hooks/common.sh`. Keep event scripts small. Use `timeout` around optional context and reminder work. Preserve existing MCP configuration and unrelated client settings. Do not add auto-staging behavior.

- [ ] **Step 5: Verify fixture and actual adapters**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_hooks -v`

Run each installed client's documented hook inspection or dry-run command. Start a disposable local client session only where the installed client offers a noninteractive smoke path. Record which adapters were runtime verified and which were fixture-only.

Expected: fixtures pass; actual supported-client smoke tests return valid payloads without changing repository or infrastructure state.

- [ ] **Step 6: Commit shared hooks**

Stage only confirmed adapter files, shared hooks, tests, and guide changes. Commit with `feat: share agent lifecycle hooks across clients`.

### Task 9: Add evidence and bounded live diagnostics

**Files:**
- Create: `scripts/agent/evidence.py`
- Create: `scripts/agent/status.py`
- Modify: `scripts/agent/__main__.py`
- Create: `tests/test_agent_status.py`
- Modify: `docs/agent-workflow.md`
- Modify: `AGENT_MAP.md`

- [ ] **Step 1: Write failing evidence and status tests**

Test timestamped evidence with target identity, probe identity, source revision or fingerprint, result, sanitized detail, and schema version. Test atomic writes and redaction with synthetic tokens and private keys.

Use fake `kubectl`, `flux`, `ping`, and read-only OPNsense probe executables to test target reporting, node readiness, Flux reconciliation, failed workloads, configured endpoint reachability, routing or BGP evidence, per-probe timeout, 30-second total budget, configurable budget, unavailable credentials, unavailable tools, partial results, timestamped JSON, and nonzero exits for failed or incomplete requested checks.

- [ ] **Step 2: Verify the tests fail**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_status -v`

Expected: import failures for evidence and status modules.

- [ ] **Step 3: Implement target discovery and probes**

Discover the Kubernetes API endpoint from `flake/hosts/*` k3s configuration and the usable kubeconfig from existing configured references. Discover OPNsense URI, TLS CA reference, and credential variable names from CI and reconciler configuration without reading secret values. Print resolved targets before probing.

Run probes with argv arrays, bounded subprocess timeouts, a monotonic total deadline, TLS verification preserved, and read-only methods only. Classify missing configuration, credentials, and tools as unavailable; timeouts and unhealthy results as failed; never translate either to healthy. Persist sanitized evidence only when requested by the command contract.

- [ ] **Step 4: Verify synthetic and authorized live behavior**

Run: `nix develop ./flake -c python -m unittest tests.test_agent_status -v`

Run: `nix develop ./flake -c just status cluster`

Run: `nix develop ./flake -c just status network`

Expected: synthetic tests pass. Live commands finish within their budget, identify targets, and return observed status or precise environmental blockers. They perform no writes or deployment.

- [ ] **Step 5: Commit diagnostics**

Stage the listed files and commit with `feat: add bounded read-only homelab diagnostics`.

## Milestone 4: Acceptance and Handoff

### Task 10: Complete the acceptance matrix and fresh-session proof

**Files:**
- Modify: `tests/test_agent_git_state.py`
- Modify: `tests/test_agent_tasks.py`
- Modify: `tests/test_agent_context.py`
- Modify: `tests/test_agent_checks.py`
- Modify: `tests/test_agent_doctor.py`
- Modify: `tests/test_agent_status.py`
- Modify: `tests/test_agent_hooks.py`
- Modify: `docs/agent-workflow.md`

- [ ] **Step 1: Map every acceptance row to an executable test**

Add a table to the operator guide naming the exact unittest method or integration command for every row in the specification's acceptance matrix. Add any missing behavior test before continuing. Documentation text alone cannot satisfy a row.

- [ ] **Step 2: Exercise a real task lifecycle**

Create a task record for this implementation with objective, acceptance criteria, session identity, explicit owned files, base commit, and next action. Checkpoint after the offline suite, run resume, edit a task-owned fixture without committing, confirm verification becomes stale, restore the fixture through a new edit, checkpoint again, and export a sanitized handoff. Do not stage unrelated files.

- [ ] **Step 3: Run final formatting and tests**

Run: `nix develop ./flake -c just fmt`

Run: `nix develop ./flake -c just fmt-check`

Run: `nix develop ./flake -c python -m unittest discover -s tests -v`

Run: `nix develop ./flake -c just check`

Run: `nix flake check ./flake`

Run: `nix develop ./flake -c yamllint .`

Run: `nix develop ./flake -c gitleaks detect --source . --redact`

Expected: every provisioned offline check passes. Any unavailable provisioned dependency remains a named blocker and prevents claiming full implementation.

- [ ] **Step 4: Measure startup and inspect repository state**

Run `just agent-context` at least five times in a warm checkout, record median elapsed time and maximum output bytes, and confirm the output stays under 6144 bytes. Run `git status --short --branch`, `git diff --no-ext-diff --check`, and inspect every task-owned diff. Confirm `docs/network/switch-port-map.md` and unrelated untracked paths were not modified or staged.

- [ ] **Step 5: Run the fresh-session handoff proof**

Start a fresh local agent session through an actually supported noninteractive client path with the exported task ID. Verify it can name the task objective, relevant source paths, remaining work, required checks, next action, and the fact that uncommitted work requires the original checkout or a patch. Record the sanitized result as evidence and label the client used.

- [ ] **Step 6: Commit acceptance evidence and documentation**

Do not commit `.agent-state/` runtime evidence. Stage only test and operator-guide changes, plus the reviewed sanitized export if it contains no machine-specific or secret material. Commit with `test: cover agent workflow acceptance matrix`.

- [ ] **Step 7: Produce the implementation report**

Report delivered commands, exact checks run and exit status, median warm startup time, maximum output size, adapter runtime verification versus fixture-only status, live probes performed with target and observation time, and remaining environmental blockers. Do not call the specification complete while any required acceptance row or command remains missing.
