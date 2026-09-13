// OpenCode project plugin: repository agent-harness adapter.
//
// OpenCode has no hooks.json; lifecycle automation ships as project plugins
// under .opencode/plugins/ (https://opencode.ai/docs/plugins/). This adapter
// gives OpenCode parity with hooks/validation-result for Bash tool failures.
//
// Upstream contract (packages/plugin/src/index.ts):
//   "tool.execute.after"(input { tool, sessionID, callID, args },
//                        output { title, output, metadata })
// The bash tool returns metadata { output, exit, description } where exit is
// the process exit code, so a failed validation command is identifiable.
// Anything unrecognized fails open: this plugin never throws and never blocks
// a tool result.

import { execFileSync } from "node:child_process";

const VALIDATION_COMMAND =
  /(^|\s)(just|nix|tofu|ruff|pyright|yamllint|kubeconform|kubectl|python|bash|gh)\s/;

export function sessionIdentity(sessionID) {
  const clean = String(sessionID ?? "unknown").replace(/[^A-Za-z0-9._-]/g, "").slice(0, 64);
  return clean || "unknown";
}

export function validationFailureRecord(input, output) {
  if (!input || input.tool !== "bash") return null;
  const command = input.args?.command;
  const exit = output?.metadata?.exit;
  if (typeof command !== "string" || typeof exit !== "number" || exit === 0) return null;
  if (!VALIDATION_COMMAND.test(command)) return null;
  return { command: command.slice(0, 200), exit_code: exit };
}

export const AgentHarness = async ({ worktree, directory }) => {
  const root = worktree || directory;
  return {
    "tool.execute.after": async (input, output) => {
      try {
        const record = validationFailureRecord(input, output);
        if (!record) return;
        const payload = JSON.stringify({
          session_id: sessionIdentity(input.sessionID),
          tool_input: { command: record.command },
          tool_response: { exit_code: record.exit_code },
        });
        execFileSync("bash", [`${root}/hooks/validation-result`], {
          input: payload + "\n",
          cwd: root,
          timeout: 5000,
          stdio: ["pipe", "ignore", "ignore"],
        });
      } catch {
        // Fail open: recording must never block tool results.
      }
    },
  };
};
