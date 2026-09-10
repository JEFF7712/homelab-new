# Home Assistant implementation review

Reviewed revision: `3fce3847ad85022a32c3561a69114db8e3e224b3`.
Implementation commits: `62b52ef` and `91e8498`.
Verdict: changes required before treating the plan as implemented.

Review scope: the two user workflows, comparison/adoption, adapters, deployment,
state ownership, and verification. No live Home Assistant writes or production
tests were performed. Reproductions used temporary directories, synthetic data,
and the implementation's mock client. Implementation files were not modified.

## Findings

### R1. P1: adoption overwrites unresolved Git changes

Location: `scripts/home_assistant/__main__.py:406-435` and
`scripts/home_assistant/source.py:176-194`.

`cmd_adopt` exports live resources and writes them without loading the baseline,
comparing Git/live changes, or checking the destination fingerprint. A separate
previous `diff` does not protect this write. With baseline alias "baseline", Git
alias "git change", and live alias "UI change", selected adoption returned 0
and replaced the Git definition. This contradicts the runbook's claim that
conflicted adoption is blocked and can erase an agent's pending source changes.

Fix: make adoption consume a selected, fresh three-way plan, reject conflicts and
changed destination files, and provide an explicit resolution path. Add regression
tests for committed Git divergence, dirty target files, and edits after planning.

### R2. P1: secret checks happen after source/capture writes

Location: `scripts/home_assistant/__main__.py:282-299,423-435`.

Neither capture nor adoption invokes the secret checks before persisting exported
definitions. An automation action with a synthetic plaintext `password` was
adopted into source successfully. Running `validate` afterward discovers the
problem too late. Capture also persists unsanitized definitions using default
filesystem permissions. API errors may carry raw response bodies into output.

Fix: validate export fields and secret boundaries before any persistence, preserve
approved secret references, reject unresolved sensitive resources, use restrictive
permissions, and sanitize errors. Test that rejected content never reaches files
or logs, including nested actions, headers, and URLs.

### R3. P1: saved plans are not bound to source, baseline, or target

Location: `scripts/home_assistant/__main__.py:580-592` and
`scripts/home_assistant/planner.py:170-195`.

The executor checks per-resource live hashes but does not validate plan instance,
Git revision/content, baseline hash, age, or application version. A fabricated
old plan naming a different instance/revision/baseline successfully created an
automation in the isolated client. If a planned source resource is later removed,
the executor can still apply its old payload and use that payload for verification.
Checks after mutation cannot make such a write safe.

Fix: bind immutable plans to an authenticated target identity, source fingerprint,
supported HA version, and baseline revision. Validate all bindings and selected
payloads before the first write. Missing/corrupt baseline requires bootstrap.

### R4. P1: failed reads can masquerade as deleted resources

Location: `scripts/home_assistant/client.py:306-349`,
`scripts/home_assistant/__main__.py:327-342,524,609`, and
`scripts/home_assistant/compare.py:32-45`.

Automation collection suppresses file/API errors and may return an empty list.
Other adapter errors use keys such as `automation/all`, but comparison only checks
exact resource keys. A failed collection therefore marks the aggregate unknown
while classifying an existing automation as a UI deletion. `plan` and inline
`apply` discard export errors entirely. The reproduction returned an empty
automation list on read timeout and misclassified an affected resource as an
experiment. With no baseline, false absence can also become a create candidate.

Fix: propagate collection completeness and kind-wide errors to every affected
resource; block plans for incomplete scopes. Never turn unknown into absence.
Do not silently fall back from core configuration to health metadata.

### R5. P1: helper and integration adapters claim success without applying or verifying

Location: `scripts/home_assistant/adapters/helper.py:63-70` and
`scripts/home_assistant/adapters/integration.py:57-66`.

`apply` is a no-op and `verify` always returns true. The planner does not enforce
observe-only ownership. Applying a nonexistent helper returned success and saved
a verified baseline although no helper was created; `verify` also returned 0.
Helper export contains only entity metadata, not the helper's actual settings.

Fix: advertise unsupported operations honestly and reject their plans before
mutation. Implement real readback even for observe-only resources. Add per-helper
configuration adapters only when the complete supported field contract is tested.

### R6. P1: protected deployment and shared baseline are missing

Location: `scripts/home_assistant/planner.py:35-58`,
`scripts/home_assistant/__main__.py:574-631,687-706`, and
`docs/runbooks/home-assistant-configuration.md`, Workflow A.

There is no CI application job consuming accepted HA configuration. The runbook
directs an agent to invoke the live apply CLI directly from the checkout. The
baseline and lock exist only in ignored checkout-local `.agent-state`. Another
checkout or a clean CI job therefore starts without the accepted baseline, loses
conflict history, and does not share apply exclusion. `verify` can checkpoint
uncommitted source without proving it was accepted/published.

Fix: implement the protected deployment job and backed-up authoritative baseline
specified by the plan. Local agents should prepare diffs/plans and read or cache
the shared baseline. Advance accepted state only after published-source validation
and verified application; maintain accurate source/content hashes.

### R7. P1: the apply lock is not an atomic or shared lock

Location: `scripts/home_assistant/planner.py:60-79`.

Lock acquisition is a check followed by ordinary file writing. Two processes can
both observe no lock and enter; separate checkouts never see each other's locks.
The lease expires without renewal even while an apply may still be running.
Read-before-write also does not exclude a UI save between the read and mutation.
The runbook overstates concurrent-edit protection and lacks the plan's editing
pause or effective exclusion requirement.

Fix: use actual atomic acquisition on the authoritative state backend, renewal,
owner-checked release, and tested crash recovery. Explicitly handle the HA UI
race without claiming local locking provides compare-and-swap.

### R8. P1: recursive canonicalization deletes meaningful configuration

Location: `scripts/home_assistant/canonical.py:171-191`.

The global volatile-field filter removes names such as `context`, `created_at`,
and `last_updated` at every depth, including user variables, action payloads, and
custom card data. Two scripts with different `sequence[].variables.context`
values hash identically; canonicalizing either removes that variable. Canonical
definitions are also used as apply payloads, so this can change behavior and hide
UI changes.

Fix: use adapter-specific, path-aware exclusion only for known runtime fields.
Preserve arbitrary user configuration and test nested variable/payload/card keys.

### R9. P2: UI deletions cannot be adopted

Location: `scripts/home_assistant/__main__.py:423-435` and
`scripts/home_assistant/source.py:165-174`.

Adoption processes only resources still returned by live export. If an automation
is deleted in the UI, selecting it reports success with zero writes and leaves
its Git file intact. The standalone source deletion helper is not connected to
the adoption command.

Fix: represent selected, baseline-backed live deletions in adoption plans. Require
explicit deletion intent and dependency checks; reject unknown selected keys.
Test deletion through the CLI, not only the source helper or comparison function.

### R10. P2: dashboard metadata updates are ignored but reported verified

Location: `scripts/home_assistant/adapters/dashboard.py:78-95,104-113`.

Title, icon, admin visibility, and sidebar settings are sent only when creating
a dashboard. Updating an existing dashboard saves just views/strategy. Verification
also ignores metadata. A title-change reproduction left the original title live
and returned true from verification, allowing the baseline to record a change
that never happened. Export additionally discards unrecognized top-level config.

Fix: reconcile dashboard metadata through the collection update API, verify both
metadata and content, and preserve or explicitly reject unsupported configuration.
Test updates separately from creation and view ordering.

### R11. P2: the declared core source is disconnected from deployment

Location: `home-assistant/core/configuration.yaml`,
`gitops/home-assistant/config.yaml`, and
`scripts/home_assistant/adapters/core.py:37-39`.

There are two independent copies of configuration. Flux deploys the embedded
ConfigMap; no generator or synchronization reads `home-assistant/core/configuration.yaml`
into it. The core adapter does nothing on apply. An agent following the documented
source path cannot deploy a recorder/core setting without discovering and editing
the second owner manually.

Fix: choose one source and deterministically generate/deliver the ConfigMap from
it, with checksum handling and validation. Reject API apply of Git-only core
resources or route them explicitly through their actual deployment mechanism.

### R12. P2: capture crashes on existing HA YAML tags

Location: `scripts/home_assistant/models.py:69-78` and
`scripts/home_assistant/__main__.py:288-299`.

Resource serialization returns raw `SecretTag` and `IncludeTag` instances, and
capture passes them to `json.dumps`. The current core source already contains
both tags. Supplying this form through the collector reproduced `TypeError:
Object of type SecretTag is not JSON serializable`. Baseline serialization has a
tag conversion helper, but capture does not use it.

Fix: use a single tested, lossless, secret-safe serialization contract across
captures, plans, JSON output, and baselines. Test the repository's actual tagged
core shape, not only the mock client's simpler configuration.

## Validation performed

- `nix develop ./flake -c python -m unittest discover -s tests -p 'test_home_assistant_*.py' -v`:
  all 29 tests passed.
- `nix develop ./flake -c bash scripts/checks/home-assistant.sh`: passed formatting,
  lint, Pyright, the 29 tests, local resource validation, and YAML lint.
- Additional isolated behavioral reproductions confirmed R1, R2, R3, R4, R5,
  R8, R9, R10, and R12. R6, R7, and R11 follow directly from source wiring.
- No production state was changed. Full repository checks, production restart
  persistence, isolated real-HA compatibility tests, and restore rehearsals were
  not run as part of this review.

The passing tests demonstrate narrow successful cases with the built-in fake
client. They do not establish the plan's conflict, secret, completeness,
cross-checkout, deployment, or round-trip guarantees.

## Repair acceptance

Add regression tests for each finding before treating the affected contract as
complete. Then demonstrate both workflows against an isolated instance of the
pinned HA version, including same-resource conflicts and UI deletions. Test
restart preservation and the protected deployment/shared-baseline path separately.
Correct coverage and runbook claims to match demonstrated behavior; unsupported
operations must fail explicitly instead of appearing successful.
