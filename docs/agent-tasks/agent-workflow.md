# Agent Task: agent-workflow

Status: `complete`

Base commit: `f154df8709a64de9fccb27a49adce2e6bdef3232`

Checkpoint HEAD: `0963bd4c74e12efd2ce5f87d7e6c8a666cd8b8a1`

Owner: `codex`

Session: `agent-workflow-2026-09-06`

## Objective

Implement and verify the agent workflow specification

## Acceptance criteria

- [x] All acceptance matrix scenarios have executable proof (docs/agent-workflow.md acceptance coverage and 151 passing tests)
- [x] Provisioned offline validation passes (nix develop ./flake -c just check exited 0)
- [x] Startup context is under one second and 6144 bytes (median 0.074473 seconds, maximum 481 bytes over five warm runs)

## Owned source

- `AGENTS.md`
- `AGENT_MAP.md`
- `justfile`
- `.gitignore`
- `.gitlab-ci.yml`
- `.claude/`
- `.codex/`
- `.cursor/`
- `hooks/`
- `scripts/agent/`
- `scripts/checks/`
- `tests/test_agent_*.py`
- `tests/test_check_entrypoints.py`
- `docs/agent-workflow.md`
- `docs/agent-tasks/`
- `docs/decisions/0001-agent-workflow-state.md`
- `docs/superpowers/specs/2026-09-05-agent-workflow-design.md`
- `docs/superpowers/plans/2026-09-05-agent-workflow.md`
- `flake/flake.nix`

## Remaining work

- None

## Verification

- `nix develop ./flake -c just check`: exit 0, evidence `/tmp/agent-final-check.log`
- `five warm just agent-context --task agent-workflow runs`: exit 0, evidence `median 0.110454 seconds; maximum 503 bytes`

## Next action

Review and merge the feat/agent-workflow branch

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
