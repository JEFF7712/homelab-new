# Remote coding-agent clients

Research date: 2026-09-12. Documentation evidence only; none of these clients were installed or authenticated during this review. Five search queries, primary product documentation used for conclusions.

## Recommended baseline

Run agent CLIs inside each person's Linux VM. Provide SSH plus one authenticated code-server instance inside that VM. Run persistent terminal sessions with tmux or supervised user services. Browser terminals invoke the same installed CLIs and repositories as SSH. Optional vendor Remote Control surfaces supplement this baseline. They introduce vendor-mediated access and account authentication, so NetBird is not the only possible ingress when enabled.

This is a design recommendation: browser/editor compatibility should not depend on proprietary agent extensions. Actual model inference remains in provider infrastructure while local tools, builds, files, and child processes execute inside the homelab VM.

## Claude Code

- CLI authentication explicitly supports SSH/container situations where the browser cannot reach its local callback: open the URL elsewhere and paste the returned code into the terminal. Subscription login and API authentication are documented. Long-lived `claude setup-token` credentials only permit inference and cannot establish Remote Control sessions. Prefer personal interactive login for users wanting Remote Control. [Authentication](https://code.claude.com/docs/en/authentication)
- Claude Desktop documents SSH environments targeting Linux/macOS: Claude runs remotely with the remote machine's files and tools. This is an optional native interface; it does not establish that the Desktop client itself is supported on every user's OS. [Desktop SSH sessions](https://code.claude.com/docs/en/desktop#ssh-sessions)
- `claude remote-control` serves a session to claude.ai/mobile while execution remains on the initiating machine. It uses outbound HTTPS rather than an inbound listening port. It requires full claude.ai authentication and a supported subscription, not API keys or setup-token credentials. A server process must remain running. Claude Code on the web's provider-hosted execution is a different product behavior. [Remote Control](https://code.claude.com/docs/en/remote-control)

## Google Antigravity

- Current documentation distinguishes Antigravity 2.0, CLI, SDK, and IDE/IDE integrations. CLI is explicitly intended for SSH/headless workflows, with native SSH and terminal multiplexer support. Do not conflate the `agy` CLI with a desktop editor launcher. [CLI overview](https://www.antigravity.google/docs/cli/overview/)
- Native Linux CLI installation and SSH OAuth are documented. SSH login prints a URL; the user authenticates in a local browser then pastes the authorization code remotely. For API-key operation, configuration must select `modelProvider: gemini` as well as supplying `GEMINI_API_KEY`. The environment variable alone is insufficient. Secure keyring handling on a fresh headless Linux VM requires a real acceptance test. [Installation and authentication](https://antigravity.google/docs/cli/install)
- `agy -p` provides noninteractive execution with text, JSON, or streaming JSON output. It uses cached credentials; an unauthenticated noninteractive run fails rather than waiting for login. [Headless mode](https://www.antigravity.google/docs/cli/headless/)
- `agy remote-control start` installs a headless daemon, implemented as a Linux systemd user service. The documentation says it starts at boot, survives logout, and restarts after crashes. The same Google account connects through the web dashboard. CLI daemon login and desktop editor login are separate. This directly supports a headless VM/browser path, without a desktop session. Verify service persistence on the selected guest OS. [Remote Control](https://www.antigravity.google/docs/remote-control/)
- Full Antigravity IDE remote SSH agent execution was not established by primary documentation reviewed within the research budget. Do not claim that a VS Code-compatible extension proves remote agent execution, nor require a GUI VM merely to support `agy`. Treat native IDE remote operation as optional pending an end-to-end smoke test.

## code-server

- code-server provides a browser editor/terminal. Its secure-access guide requires authentication and encryption and documents reverse-proxy and SSH-forwarding approaches. WebSockets must work. For LAN access without NetBird and browser-only devices, use HTTPS with individual workspace authentication; keep the listening service behind the chosen boundary. [Secure access](https://coder.com/docs/code-server/guide)
- It is not identical to Microsoft VS Code. It uses Open VSX; Microsoft Marketplace and proprietary Remote extensions are not a portable baseline. A browser terminal running the agent CLIs avoids assuming agent extensions are available or licensed for code-server. [FAQ](https://coder.com/docs/code-server/FAQ)

## Acceptance tests for implementation agents

1. For each CLI, record installed version and supported guest platform. Sign in with one user's own account over SSH from a client browser, then repeat through code-server's terminal. Do not print or export credentials into shared logs or images.
2. Ask each agent to run `hostname`, report its working directory, create a task-owned file, and run a small build. Independently inspect VM processes/files and confirm nothing ran on the laptop except the client interface.
3. Start a long task in the documented persistent session mechanism; disconnect SSH, close the browser, reconnect, and verify the same task completed. Test reboot separately: service restart is not a promise that an interrupted agent task resumes safely.
4. Test Claude and agy Remote Control separately if enabled. Confirm personal account binding and that the execution host remains the VM. Record the resulting vendor-mediated access path in the access inventory.
5. On a new headless guest, prove login storage and renewal survive logout/reboot. Verify agy's user service and keyring behavior without a desktop session. Test revoked credentials and expired sessions for actionable errors.
6. From LAN with NetBird stopped, access SSH and HTTPS code-server. From an external network, repeat through the authorized NetBird identity. Verify an unauthenticated browser and another user's credentials cannot enter the workspace.
7. Run network-denial checks through agent tools, terminal shell, browser automation, and containers. Client settings and instruction files are not isolation boundaries.
8. If users request native Antigravity IDE support, separately prove the agent's tools, extension host, terminal, browser automation, and writes execute in the VM. Local editing of remote files alone does not satisfy this test.

## Limitations

Product support, account eligibility, packaging, and daemon behavior can change. Pin tested versions in the implementation evidence and recheck these URLs before rollout. Codex is outside this delegated research scope and must be verified from its official documentation separately. No provider account-sharing or centralized billing model is assumed.
