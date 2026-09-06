#!/usr/bin/env bash
set -euo pipefail
HOOKS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC2034
REPO_ROOT=$(cd "$HOOKS_DIR/.." && pwd)
hook_load() { [[ ${AGENT_HOOK_ACTIVE:-0} != 1 ]] || return 1; HOOK_INPUT=$(cat); command -v jq >/dev/null 2>&1; }
hook_session() { jq -r '.session_id // .conversation_id // "unknown"' <<<"$HOOK_INPUT"; }
hook_event() { jq -r '.hook_event_name // .event // empty' <<<"$HOOK_INPUT"; }
hook_ok() { printf '%s\n' '{}'; exit 0; }
hook_context() { jq -n --arg value "$1" '{hookSpecificOutput:{additionalContext:$value},additional_context:$value}'; }
