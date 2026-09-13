# Home Assistant access boundary findings

Date: 2026-09-12. Scope: read-only source and official upstream documentation review. No live permission probes or infrastructure changes were performed. Upstream version-specific evidence is 2026.9.2, not proof of the deployed version.

## Findings

1. **Normal nonadministrator accounts cannot author automations through the configuration API.** Automation configuration inherits the generic edit view, whose GET, POST, and DELETE methods require an administrator. A service retaining administrator credentials can deploy on their behalf without granting guest accounts administration. Sources: [automation configuration implementation](https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/config/automation.py), [2026.9.2 configuration edit view](https://raw.githubusercontent.com/home-assistant/core/2026.9.2/homeassistant/components/config/view.py).

2. **Native entity permission machinery exists, but it is not sufficient evidence for a supported, comprehensive bedroom boundary.** Policies support entity/device/area/domain grants, while administrative permission is separate. Owner bypasses restrictions; service handlers must propagate user context and perform checks. Official custom-group instructions are an old experimental storage-edit procedure, not evidence of a supported current user-facing feature or an audited security boundary. Do not recommend editing `.storage/auth` as the production solution. Sources: [permissions](https://developers.home-assistant.io/docs/auth_permissions/), [official custom-group discussion](https://developers.home-assistant.io/blog/2019/03/11/user-permissions/). The latter explicitly dates from 2019 and is historical evidence only.

3. **Automation YAML is a capability-bearing program.** Actions can invoke scripts, scenes, events, and templated targets; shell-command actions can execute configured commands, and REST-command actions can initiate configured HTTP requests. Allowing an automation file is therefore not equivalent to allowing household device control. A YAML schema check cannot establish authorization. Sources: [script syntax](https://www.home-assistant.io/docs/scripts/), [shell command](https://www.home-assistant.io/integrations/shell_command/), [RESTful command](https://www.home-assistant.io/integrations/rest_command/).

## Repository evidence

- `docs/runbooks/home-assistant-configuration.md` defines source-first validation, planning, protected CI deployment, readback, and shared baselines. It requires pausing UI edits on target resources because HA lacks transactional compare-and-swap. Existing locking protects cooperating writers, not a concurrent independent UI writer.
- `scripts/home_assistant/client.py` reads configuration through Kubernetes pod execution and uses Kubernetes ConfigMaps for baseline/lease state. This client and its kubeconfig belong in trusted deployment infrastructure, never in guest VMs.
- `scripts/home_assistant/adapters/automation.py::validate` currently checks mapping shape and required fields. It is not a guest authorization policy engine.
- `.gitlab-ci.yml` deploys HA through the `nas-privileged` runner. Guest repository code, hooks, CI YAML, dependency installation, or helper scripts must never execute on that runner.
- `home-assistant/automations/away_lights_off_restore.yaml` already mixes bedroom and stairs devices, creates a snapshot scene, and uses dynamic targets. Bedroom separation requires migrating mixed automations too, not merely moving three light entities.

## Recommended design constraints

### Independent deployment

Use a guest contribution repository containing data only, plus a trusted broker and deploy worker whose code, policy, and credentials guests cannot change. Authenticated users submit structured automation intent; a trusted compiler produces canonical YAML from a documented supported subset. Persist accepted desired state in the owning repository and use the authorized CI deployment contract with an immutable source/policy identity, lease, conflict checks, and verified readback. Return a job status and actionable validation failures without requiring Rupan's routine review. Repository authorization must explicitly permit this bounded unattended path before implementation.

The compiler should default-deny unknown syntax, integration actions, templated action names/targets, arbitrary events, unrestricted script/scene/automation invocation, MQTT publication, shell/REST/Python/command actions, and configuration/reload/system administration. Permit household actions individually with typed data, explicit entity targets, bounded branching/delays/repeats, and appropriate quotas. Recursively validate every nested action. Templates require an explicitly constrained language or runtime mediation; do not attempt to secure arbitrary Jinja with a few banned strings. Expand approved blueprints under trusted control before validation. Reject unknown YAML tags, duplicate keys, path traversal, oversized/deep payloads, and guest-controlled build commands.

Shared-device control does not require ownership isolation between guests, but record the actor, canonical input, policy version, target revision, deployment result, and rollback version. Serialize updates and reject stale revisions. Quotas must bound deployed execution frequency/concurrency as well as HTTP request rate. Keep privileged/infrastructure automations outside guest-editable scope even when they use shared devices.

### Runtime and UI access

A guest VM with root can copy its owner's HA token or use a browser; protecting the broker alone does not constrain direct HA access. Inventory and test all services callable by normal HA users, including installed custom integrations, existing scripts/scenes, and actions accepting URLs or other network destinations. Constrain HA's own outbound access to its required dependencies so it cannot become a generic relay into management networks. Guest workspace rules must also cover HA's public hostname, not only its private address.

Existing users can operate from their LAN devices or public HA UI independently of the workspaces. A workspace firewall cannot restrict those paths. Either enforce the same policy across every access path or clearly scope the guarantee to the agent VMs and acknowledge that existing HA accounts retain their current capabilities.

### Bedroom lights

For a strong boundary across the HA UI, API, and automations, prefer a separate private HA instance or private device controller for Rupan's bedroom. Guest-facing HA must not possess the bedroom integration credentials, MQTT topic rights, controller endpoint access, or scripts/scenes that control those lights. Preserve a private Rupan UI. A unified owner dashboard is a later integration concern, not a reason to bridge bedroom control back into guest HA.

This is a proposed architecture, not a proven deployment recipe. First inspect the Roku bridge runbook and current credential/account scope: one cloud account or broad MQTT credential may span private and shared devices. Split credential/topic ownership and network paths before claiming isolation. Test actual device effects for direct service calls, all-device/area targets, scenes, scripts, events, MQTT, and restored backups. If separation is too disruptive, report bedroom protection as deferred explicitly; dashboard hiding is not protection.

## Acceptance evidence needed during implementation

- A normal guest can create and update a permitted shared-device automation and observe verified deployment without Rupan approving each change.
- Guest configuration API calls fail; guests cannot retrieve HA administrator credentials or Kubernetes/deployment credentials.
- Malicious nested actions, templated targets, scene/script indirection, arbitrary MQTT/HTTP calls, unapproved blueprint expansion, and attempts to alter trusted pipeline code fail before deployment.
- Guest tokens, API requests, browser UI, and LAN/remote paths cannot control bedroom devices if bedroom isolation is included.
- Changing or re-enabling an owner infrastructure automation is rejected; two concurrent guest changes have deterministic conflict behavior.
- Actual blocked network attempts from a root guest VM and from any allowed HA relay surface verify the homelab boundary, with IPv4 and IPv6 coverage.

Open uncertainties: deployed HA version and integrations, users' current roles, exposed public/LAN endpoints, available service relays, and Roku/MQTT account boundaries need fresh runtime inventory before implementation. No broad native entity isolation claim is justified by the sources reviewed.
