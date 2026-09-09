# Home Assistant configuration ownership and UI adoption

Status: implementation plan, not implemented or deployed.
Date: 2026-09-09.
Prepared against repository revision `2b2a46584688aa85a53d24170233b51031798307`.

## 1. Objective and user contract

Make Home Assistant configuration understandable, reviewable, and reproducible
by an AI agent while preserving the user's ability to experiment in the UI.
Git holds accepted desired configuration. Home Assistant holds the current
working configuration. A verified baseline records the last configuration
accepted in Git and observed in Home Assistant.

There are two equally supported ways to make changes. The user does not need
to edit Git files or know the CLI commands for either workflow.

### Workflow A: ask an agent to make a change

1. The user describes the desired behavior to an agent in natural language.
2. The agent reads accepted Git configuration and captures fresh live state,
   including actual entity identities, capabilities, and any unadopted UI edits.
3. The agent translates the request into a focused desired-configuration diff
   in Git. It preserves unrelated experiments and resolves conflicting intent
   explicitly rather than silently resetting live state.
4. The agent validates the candidate, prepares the apply plan, and publishes and
   deploys through the authorized repository path. Existing authorization carries
   forward; any required publishing/deployment approval is for the concrete diff.
5. The agent verifies live configuration and required reloads, checkpoints the
   baseline for the successfully reconciled scope, and reports the resulting
   behavior. A local source edit alone does not complete a request to change HA.

Agent-authored configuration uses the same writable HA representations as
UI-authored configuration wherever supported. The user must be able to edit an
agent-created automation or storage dashboard in the UI afterward. The default
agent path is source-first, not an unrecorded live mutation followed by an export.

### Workflow B: experiment in the UI, then ask an agent to adopt it

1. The user edits and saves something in the Home Assistant UI.
2. The change takes effect in Home Assistant immediately where HA supports it.
3. An agent captures configuration and reports semantic differences from the
   baseline and current Git source.
4. The agent prepares a selected, local Git diff adopting the experiment.
5. Validation runs before publishing through the repository's authorized path.
6. Deployment verifies that live configuration matches the accepted source.
7. Only then does the shared baseline advance.

The user may ask for adoption later, or never. No explicit experiment mode,
pre-registration, or immediate agent invocation is required. Pending UI changes
remain live and appear as drift until adopted or explicitly reverted.

In this context, requests such as "reconcile my UI changes" or "sync what I
changed back to Git" mean capture and adopt live changes into source. They must
not default to overwriting the UI from Git. Show the detected scope, prepare the
local diff, validate, and complete authorized publishing and verification. If the
user explicitly requests reverting to Git, use the separate revert workflow.
If both Git and live configuration changed incompatibly, report the conflict and
obtain the missing intent before overwriting either version.

Both workflows share resource identities, canonicalization, comparison,
validation, deployment, and baseline records. Either can follow the other on
the same resource without a migration or a change of ownership mode.

UI experiments must survive ordinary pod restarts and unrelated Flux syncs.
Detection never restores Git automatically. Applying a Git change must stop
when it would overwrite an unadopted UI edit. Explicit revert is a separate,
reviewable operation. Git adoption does not itself mutate Home Assistant.

This is controlled reconciliation, not automatic bidirectional synchronization.
An experiment is already live, not an isolated sandbox. The adoption tool must
not execute automation actions, scenes, scripts, or device commands to test them.

## 2. Verified starting point and required discovery

Repository observations, not live-state assertions:

- `gitops/home-assistant/config.yaml` contains only `default_config` and recorder
  database configuration. There are no explicit automation/script/scene includes.
- `gitops/home-assistant/deployment.yaml` copies `configuration.yaml` into the
  persistent config volume on every pod start. Preserve its Git ownership, but
  do not extend this unconditional copy to UI-editable resources.
- `/config` is persistent; `secrets.yaml` is mounted from an ExternalSecret.
- Home Assistant uses one replica and `Recreate`; a restart implies interruption.
- The Flux Kustomization in `gitops/clusters/homelab-01/home-assistant.yaml` points
  at `gitops/registry-cutover/components/home-assistant`, not directly at the base.
- The Deployment pins the container by digest. Its application version and live
  integration inventory have not been inspected for this plan.
- Existing agent commands live under `scripts/agent/`; checks are exposed by
  `just check-changed`, `just check`, and `just fmt-check`.

Before implementation, run `just agent-context`, inspect status and governing
instructions, and reread the affected sources. Before live work, identify the
cluster, namespace, HA instance, running version, image digest, Flux revision,
config PVC, and backup coverage. Use authenticated, bounded, read-only discovery.
Never infer actual configuration from the deployment manifest alone.

Inventory all configuration surfaces, including installed custom integrations,
custom cards, blueprints, dashboards, helpers, registries, config entries, user
preferences, and integrations with credentials. Record capability counts and
unsupported resources without exposing values. Inspect existing automation,
script, and scene files before adding includes or initializing anything.

## 3. Architecture decisions

### 3.1 Keep UI resources writable

Do not convert UI dashboards into YAML-mode dashboards merely to put them in Git.
Keep them in HA storage mode and export their accepted definitions as YAML in
Git. Publish changes through a version-tested dashboard adapter.

Keep UI automations, scripts, and scenes in HA's normal writable files and edit
them through HA's own configuration interfaces where supported. Add explicit
includes for `automations.yaml`, `scripts.yaml`, and `scenes.yaml` after inventory
and validation. Git stores resource definitions separately for review; adapters
translate those definitions into HA's supported representation.

Reserve packages and directly mounted/copied YAML for resources deliberately
owned by Git, such as core configuration and YAML-only integrations. A resource
must never be declared both in a package and in a UI-managed collection.

### 3.2 Separate pure planning from effects

Implement typed Python modules with four boundaries:

- Collectors read HA configuration and produce validated resource documents.
- Canonicalization and comparison are pure, deterministic functions.
- Adoption writes selected local source files atomically after preflight.
- Apply adapters mutate HA only from a validated deployment plan and verify it.

Provide machine-readable output and a concise human summary. The LLM interprets
intent and reviews changes; deterministic code handles identity, serialization,
conflict detection, secret boundaries, and writes. No LLM is required in CI.

### 3.3 No automatic drift correction

Default policy is `observe`. An optional scheduled collector may report drift,
but it cannot commit, push, apply, or discard changes. An explicit authorized
deployment applies Git changes through the same conflict-aware planner.

Do not implement a background controller that continually forces live state to
Git. It would erase the user's experiments. If an experimental session marker
is added, it is advisory; drift protection must work without the user setting it.

### 3.4 API compatibility is explicit

HA's frontend uses configuration endpoints beyond the public REST state API.
Treat these as version-dependent application interfaces. Inspect source at the
actual deployed release and test each adapter against that release. Do not use
the development branch as the implementation contract.

`/api/states` is not a configuration export. Entity states and attributes must
not substitute for automation definitions, integration options, or registries.
Do not implement direct `.storage` writes. An unsupported API becomes a reported
coverage gap, not a reason to modify internal storage.

## 4. Coverage and ownership model

Every inventoried resource gets exactly one category:

| Surface | Intended management | Limits and implementation order |
| --- | --- | --- |
| Core configuration, recorder, YAML-only integrations | Git-owned YAML | Preserve secret references; restart/reload classification |
| UI automations, scripts, scenes | Git accepted definition, writable HA working copy | First adapters; preserve IDs and editor compatibility |
| User-created storage dashboards | Git accepted definition, API apply | First adapters; preserve card/view order and custom content |
| Existing YAML dashboards/packages | Git-only | Detect ownership conflicts; no promise of visual editing |
| Areas, floors, labels | Registry adapters | Add after core round-trip workflow |
| Entity/device names, assignments, visibility | Allowlisted registry fields | Do not adopt discovery/runtime fields; preserve integration identity |
| Helpers | Per-helper adapters | YAML support and config-entry support differ by helper type |
| Integration options and nonsecret setup parameters | Per-integration adapters | Never promise generic config-entry replay |
| OAuth, pairing, reauthentication, user credentials | Secret/runtime owner plus recovery procedure | Human or integration-specific flow may be required |
| Energy, Assist, built-in dashboard settings, user preferences | Capability audit, then explicit adapters | Unsupported fields remain reported and backed up |
| Blueprints, custom integrations, custom frontend assets | Pinned source artifacts and dependency inventory | No unreviewed downloads during adoption or validation |
| History, recorder data, traces, sessions, current device states | Runtime state and backups | Excluded from configuration diffs |

Publish a coverage document listing each discovered kind/integration, readable
fields, writable fields, secret handling, identity rules, and tested HA versions.
Use statuses `managed`, `observe-only`, `runtime-only`, and `unsupported`.
Missing coverage must be visible in every inventory summary. Completion means
every discovered surface is classified, not a false claim that all HA settings
are declaratively replayable.

## 5. Proposed repository and runtime layout

These are new paths to implement, not existing commands or interfaces:

```text
home-assistant/
  inventory.yaml
  core/configuration.yaml
  automations/<stable-key>.yaml
  scripts/<stable-key>.yaml
  scenes/<stable-key>.yaml
  dashboards/<stable-key>.yaml
  registries/{areas,floors,labels,entities,devices}.yaml
  helpers/<stable-key>.yaml
  integrations/<stable-key>.yaml
  dependencies.yaml
  coverage.yaml
scripts/home_assistant/
  __main__.py
  models.py
  canonical.py
  compare.py
  source.py
  client.py
  adapters/
tests/test_home_assistant_*.py
docs/runbooks/home-assistant-configuration.md
.agent-state/home-assistant/<instance>/<capture-id>/
```

Create files only when a real resource or implemented capability needs them.
Do not ship empty integration adapters or fabricated example devices. Keep
Kubernetes manifests in `gitops/home-assistant/`; do not place raw HA YAML in a
directory that existing checks assume consists entirely of Kubernetes objects.
Add explicit check routing for `home-assistant/`.

Local captures and plans are ignored, restrictive-permission artifacts with
bounded retention and explicit cleanup. Ignoring a directory does not make it a
secret store. Raw credential-bearing responses should never be persisted.

Persist the verified baseline and identity mappings in a backed-up, dedicated
runtime directory, separate from HA internal storage. Include HA instance
identity, source commit and content hash, schema/adapter versions, timestamps,
resource hashes, and sanitized canonical accepted definitions needed for a
three-way comparison. Local agents may read/cache this record but cannot advance
the authoritative deployment baseline just by exporting or adopting files.

## 6. Data model, canonicalization, and identity

Each source resource has a schema version, kind, stable logical key, owner mode,
and desired configuration. Keep volatile capture metadata out of desired files.
Store deployment IDs in an instance-specific binding map when portability
requires them; retain intrinsic stable IDs such as automation IDs where valid.

- Never match solely by friendly name. Renames must preserve identity.
- Fail on duplicate keys, ambiguous bindings, and cross-instance capture use.
- Preserve action sequences, dashboard view/card order, templates, multiline
  strings, scalar types, and meaningful omitted-versus-null values.
- Sort mapping keys only where semantically safe; never blanket-sort arrays.
- Reject duplicate YAML keys and arbitrary executable YAML tags. Explicitly
  handle permitted HA tags such as secret/include references without evaluating
  them or reading paths outside the permitted source tree.
- Exclude runtime timestamps and computed fields using per-adapter field rules.
- Preserve unknown nonsecret configuration only if the adapter can round-trip it
  safely. Otherwise report unsupported, rather than silently dropping it.
- Retain native device/entity references initially. On restore to a new instance,
  require explicit bindings; do not heuristically rewrite device IDs in templates.
- Detect references to missing entities, scripts, blueprints, integrations, and
  custom cards. Distinguish unavailable-but-known entities from missing IDs.

Acceptance invariant: export, canonicalize, apply, export produces the same
semantic document, and a second comparison is empty.

## 7. Three-way comparison and conflict policy

Let B be the last verified accepted baseline, G the current Git desired resource,
and L a fresh live capture. Compare canonical definitions, including existence.

| Condition | Classification | Default action |
| --- | --- | --- |
| B = G = L | Clean | None |
| G = B, L differs | UI experiment | Offer local adoption; block overwrite |
| L = B, G differs | Git change | Eligible for planned deployment |
| G = L, both differ from B | Already converged | Verify published source, then checkpoint |
| G and L both differ from B and each other | Conflict | Show all three; require explicit resolution |
| No baseline | Uninitialized | Inventory/bootstrap only; no automatic overwrite |
| Capture incomplete or unreadable | Unknown | Fail affected plan; never interpret as deletion |

Treat a resource atomically initially. Do not automatically merge disjoint
fields inside the same automation or dashboard. An agent can prepare a merged
candidate and rerun validation, but the tooling must expose that as a resolution.

Additions follow the same rules with absence represented explicitly. Adopted
deletions require resource selection and deletion intent. Git absence must not
delete unowned live resources. Remove only resources previously managed by this
system and explicitly selected for deletion; check dependent references first.
Renames are updates under stable identity, not delete/create operations.

## 8. Command contracts

Expose `python -m scripts.home_assistant` with matching `just ha-*` recipes.
All names below describe interfaces to build:

| Command | Effects and required output |
| --- | --- |
| `inventory` | Read-only capability, version, ownership, and reference inventory |
| `capture` | Read-only bounded collection; sanitized local snapshot with completeness metadata |
| `diff` | Compare B/G/L; report resource-level changes, conflicts, exclusions, and secret-review blocks |
| `adopt` | Apply selected live definitions to local source; never stage, commit, push, or change HA |
| `validate` | Offline schema/reference/secret checks; separate opt-in HA-version validation |
| `plan` | Immutable apply plan tied to Git content, live hashes, baseline revision, and target identity |
| `apply` | Authorized deployment entrypoint; reject stale plans, verify each write, journal progress |
| `verify` | Fresh readback, semantic equality, health and reload results; advance baseline only when valid |
| `revert` | Produce/apply an explicit plan restoring selected live resources from accepted Git |

Use structured JSON with schema version, command, instance, status, resources,
coverage, and sanitized errors. Define stable exit codes: 0 successful/clean,
1 drift or pending change, 2 conflict/invalid/stale, 3 unavailable/incomplete.
Mutation success can return 0 while indicating remaining drift elsewhere.

Selection must support explicit resource keys and reviewed plan files. No
implicit whole-instance adoption or deletion. Refuse unsafe filenames, traversal,
symlink escapes, overwriting unrelated WIP, or a changed source fingerprint.
Preflight all selected writes before touching source. Use atomic replacements
and recoverable local transaction records for multiple-file edits.

## 9. Secrets and trusted data boundaries

Continue existing SOPS/ExternalSecret ownership. Desired configuration contains
secret references, not access tokens, passwords, OAuth blobs, or raw config-entry
data. Resolve secrets only inside the authorized execution environment.

Adapters must use allowlisted export fields and mark credential-bearing settings
as nonexportable or secret-reference substitutions. Free-form templates, URLs,
webhook paths, headers, and automation action data can also contain credentials.
Run secret detection before writing candidate Git content, but do not claim a
scanner proves arbitrary free text is secret-free. Unresolved sensitive values
block adoption of that resource and receive a sanitized review report. Never
replace a hidden value with a redaction string that could later be deployed.

Load HA credentials from an approved secret file/environment reference, never
CLI arguments or committed manifests. Verify TLS; use an authenticated internal
route or approved tunnel rather than disabling certificate checks. HA access
tokens may have broad user privileges; do not invent per-resource token scopes.
Separate read-only tool behavior from underlying credential privilege in docs.

Treat imported names, descriptions, dashboard Markdown, and templates as untrusted
data. They cannot issue agent instructions, execute shell commands during export,
or direct secret retrieval. Logs report resource keys and sanitized errors only.

## 10. Deployment, concurrency, and restart behavior

Flux continues to own Kubernetes resources. Implement application configuration
delivery as a protected CI operation using the shared planner, after Flux has
made required infrastructure/source bundles ready. The runtime job consumes an
immutable accepted Git artifact. It does not clone arbitrary MR code with HA
credentials, and the quality runner never receives deployment credentials.

Inspect existing runner configuration before choosing the execution lane.
Provision any new runner secret or permissions through the authorized repository
workflow. Do not use an ad hoc laptop apply as the production deployment path.

The implementation must distinguish:

1. Git-only core files: deploy deterministically, validate before restart, and
   update pod-template checksums for configuration-sensitive changes.
2. UI-editable files/storage: preserve on restart; mutate through adapters only.
3. Shared baseline: update after verified application, never from pod startup.

Serialize applies using one instance-level lock, with owner/revision/expiry and
crash recovery. Immediately before each write, reread the resource and compare
against the plan. Retry reads with bounded backoff, but never blindly retry an
uncertain mutation. On timeout, read back to determine whether the write landed.

HA interfaces may not offer compare-and-swap. A local apply lock does not lock
the HA UI. Read-before-write reduces risk but cannot eliminate a simultaneous
UI save racing the write. For live mutation, require a brief user editing pause
or a verified mechanism that actually excludes concurrent editors. Document the
remaining race honestly. If a stronger no-lost-edit guarantee is required, block
apply until effective exclusion is implemented; do not claim hash checks provide it.

Keep sanitized before/after hashes and a per-operation journal. Verify after each
write and again for the complete plan. On partial failure, halt dependent writes,
retain the previous accepted baseline, and report applied/pending/conflicted
resources. Recovery compares live state with both journal and baseline.
Rollback itself uses fresh conflict checks; it must not overwrite a newer UI edit.

HA has no assumed cross-resource transaction. Order dependencies before their
consumers, defer removals, and record required reload/restart actions per adapter.
Do not claim configuration changes are atomic or zero-downtime.

## 11. Bootstrap and migration

1. Complete live inventory and version-specific capability probes without writes.
2. Verify current backups of `/config`, secret material, and PostgreSQL. Recorder
   dumps alone do not preserve UI configuration. Document a restore procedure.
3. Capture current supported resources and classify all unsupported surfaces.
4. Prepare a sanitized initial desired-state import locally; preserve current IDs.
5. Implement and test collectors/diffs before enabling any live mutation.
6. Add core includes only after confirming existing files and avoiding duplicate
   package ownership. Create missing writable files only when actually absent.
7. Publish through the authorized Git/CI/Flux path. Initial adoption should require
   no semantic write to already matching UI resources.
8. Initialize the baseline only after verifying accepted Git equals current live
   configuration. If the UI changed meanwhile, recapture and resolve first.
9. Prove a UI edit survives restart and an unrelated Flux reconciliation before
   enabling routine deployments of UI-editable resources.
10. Enable optional scheduled detection after manual capture/adoption is proven.

Do not rebuild integrations or recreate registry objects during bootstrap.
Do not perform full `.storage` imports as declarative migration. Existing config
and credentials remain authoritative runtime state until an adapter explicitly
manages their nonsecret settings.

## 12. Work packages and acceptance gates

Implement serially in logical commits; inspect combined behavior after each gate.

### A. Inventory and contracts

Deliver coverage schema, command envelopes, ownership model, target identity,
and version capability probes. Add an operator runbook explaining experiments,
adoption, publishing, conflicts, and restore boundaries.

Gate: every discovered configuration surface has an explicit category; no
credentials appear in generated inventory; unavailable reads are not empty lists.

### B. Pure comparison and local adoption

Implement models, canonicalization, identity bindings, baseline storage format,
three-way comparison, selected source edits, and offline validation.

Gate: deterministic round trips; conflict/addition/deletion truth table tests;
unrelated WIP remains byte-identical; no baseline advancement on adoption.

### C. Initial collectors and writable adapters

Implement automations, scripts, scenes, and storage dashboards against the pinned
HA release. Use the frontend configuration APIs where verified. If API listing
is incomplete, a narrowly allowlisted read-only file collector is acceptable for
the corresponding YAML files. Writes still require a tested HA-mediated route;
otherwise explicitly mark the affected kind observe-only until resolved.

Gate: import existing definitions without identity changes; create/edit/delete
round trips in an isolated instance; UI editing continues after application.

### D. Protected deployment and recovery

Wire configuration bundle delivery, secret resolution, CI execution, locking,
freshness checks, journals, readback, baseline checkpointing, and restart behavior.
Update image inventory/checksums if new workload images or config inputs require it.

Gate: stale plans rejected; partial failures recoverable; second apply has no
writes; unadopted UI changes block conflicting deployment; no MR credential access.

### E. Broaden coverage

Add registry adapters, supported helper types, integration-specific nonsecret
options, and remaining user-used settings in that order. Track custom assets and
blueprint dependencies. Each addition needs its own field/secret/identity contract.

Gate: every installed integration and configuration surface has tested management
or an explicit observed/unsupported/runtime classification and recovery procedure.
Do not leave stub adapters or imply this gate makes all integrations replayable.

### F. Production migration and handoff

Run the migration after deployment authorization, exercise acceptance scenarios,
and export an implementation handoff with source revision, tested HA version,
coverage, validation results, live evidence, recovery steps, and limitations.

Gate: another agent can detect an actual UI edit, adopt it into a focused local
diff, validate it, and explain any remaining changes without relying on chat history.
Also prove the reverse entrypoint: a natural-language request becomes a validated
Git change, is deployed and verified, and remains editable in the live UI. The
runbook must provide agent procedures for both entrypoints and define "reconcile
UI changes" as adoption toward Git unless the user explicitly requests a revert.

## 13. Verification matrix

Routine tests use synthetic, credential-free fixtures and fake transports.
An isolated HA instance must use the production image version, temporary storage,
and no production integration credentials or access to real devices. Do not
restore production config into a test instance that could control the home.

| Scenario | Required evidence |
| --- | --- |
| No change | Empty semantic diff and zero apply calls |
| Agent-requested change | Fresh inventory informs the Git diff; authorized apply/readback completes the request |
| Agent edit followed by UI edit | Resource remains UI-editable; later adoption preserves its identity |
| UI edit followed by agent request | Unrelated experiment survives; same-resource conflict requires explicit resolution |
| User asks to reconcile UI changes | Adoption toward Git; no implicit live reset or action execution |
| UI-only edit | Classified as experiment; local adoption matches live; baseline unchanged |
| Git-only edit | Planned update; verified readback; baseline advances only after published source verification |
| Both sides changed differently | Conflict and zero writes |
| Both sides independently converge | No mutation; verified baseline checkpoint |
| UI edit between capture and apply | Stale plan refusal where observed; editor exclusion/race limits documented |
| Dashboard card/action order | Exact semantic order preserved after round trip |
| Resource rename | Same identity, no duplicate object |
| Resource deletion | Explicit selection, dependency check, no deletion of unmanaged resources |
| Read failure/pagination/incomplete response | Unknown/incomplete, never inferred deletion |
| Secret in action/header/URL/config entry | No plaintext source/log leak; blocked export or approved reference |
| Unknown fields, YAML tags, duplicate keys | Explicit validation result; no silent data loss or execution |
| Pod restart/unrelated Flux sync | Unadopted experiment remains intact |
| Unauthorized/expired token/version mismatch | Sanitized actionable error, no mutation |
| Interrupted apply or ambiguous timeout | Journal and readback identify actual progress; no blind replay |
| Lost baseline/new instance | Bootstrap required, no mass overwrite |
| Adoption with unrelated dirty files | Only selected owned files change |
| Restore rehearsal | Config state and bindings recovered; excluded state and reauthentication requirements reported |

Run repository checks in the pinned environment: scoped Python behavior tests,
Ruff/Pyright, HA config/reference validation, Kustomize/schema validation for
changed manifests, secret scanning, `just check-changed`, and `just fmt-check`.
Run `just check` for final integration handoff. Report missing prerequisites or
failed unrelated gates precisely. Static validation does not prove live adoption,
UI persistence, HA reload success, or restore behavior.

## 14. Definition of done

- UI editing remains usable for all managed UI-capable resource kinds.
- Both natural-language agent requests and UI-first experiments work end to end
  on the same supported resources without the user manually editing source.
- Experiments survive normal restarts and are never silently forced back to Git.
- Agents can obtain an accurate, sanitized inventory and focused three-way diff.
- Selected adoption yields validated, reviewable local source changes.
- Authorized deployment applies only nonconflicting changes and verifies results.
- Source, live state, baseline, secret state, and runtime-only state have explicit owners.
- A second apply is a no-op; failures and unsupported surfaces are visible.
- All discovered configuration categories are accounted for, with honest limits.
- Backups and a tested recovery path cover state that Git cannot recreate.
- No changes are published or deployed solely because this plan was requested.

## 15. Upstream references and implementation cautions

Reviewed on 2026-09-09. Documentation and development sources establish direction;
the implementing agent must replace development references with the deployed
release's source when establishing adapter contracts.

- [Automation editor](https://www.home-assistant.io/docs/automation/editor/): UI
  saves activate automations, and the automation file include is required.
- [Dashboard configuration](https://www.home-assistant.io/dashboards/dashboards/):
  storage dashboards and YAML dashboards are distinct management modes.
- [WebSocket API](https://developers.home-assistant.io/docs/api/websocket/):
  authentication and message framing for the client transport.
- [Automation configuration implementation](https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/config/automation.py):
  starting point for version-specific automation API inspection.
- [Script configuration implementation](https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/config/script.py):
  starting point for script adapter inspection.
- [Lovelace WebSocket implementation](https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/lovelace/websocket.py):
  starting point for dashboard read/write capability inspection.

The official MCP integration may expose useful agent operations, but it is not
a substitute for the ownership, diff, adoption, and deployment contracts above.
An MCP wrapper around this CLI can be added later only if there is a concrete
consumer; the initial deliverable is a tested CLI and repository workflow.
