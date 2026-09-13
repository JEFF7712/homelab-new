# Multiuser agent workspace research

Question: How should this homelab host two to four personal cloud-agent development environments with SSH and browser access, LAN and NetBird entry, independent shared Home Assistant automation deployment, and enforced separation from other infrastructure?

Research tracks:

1. Home Assistant permissions and safe independent automation deployment. Establish native permission limits, bedroom-light protection, and indirect paths outside HA.
2. Remote development clients. Verify Claude Code and Google Antigravity support for remote Linux execution, browser access, authentication, and persistent sessions.
3. Network and virtualization architecture. Verify NetBird identity/routing controls and a small VM-based implementation, including enforcement outside guest administrator control.

The primary agent will inspect repository ownership, live capacity where accessible, Codex support, and existing HA deployment code. Findings will be synthesized into a repository implementation plan with explicit assumptions, source ownership, phased tasks, acceptance tests, deployment authorization, and rollback. Research is read-only; only documentation will be written.
