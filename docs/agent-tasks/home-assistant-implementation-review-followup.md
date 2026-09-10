# Home Assistant implementation review, follow-up

Reviewed commit: `36c0d347896ca276ef30fe95e1a7f33cbbb060ad`.
Previous review: [initial findings](home-assistant-implementation-review.md).
Verdict: changes required. The fixes improve individual cases, but the combined
workflow still has data-loss, synchronization, and deployment failures.

Review used current source, the scoped validation gate, and isolated behavioral
reproductions in temporary directories. No live configuration, secrets, cluster
resources, or implementation files were changed.

## Improvements confirmed

- The original three-way conflict adoption example is rejected.
- Password-field capture/adoption checks now run before persisting resource data.
- Helper/integration mutations are rejected and verification reads actual state.
- Nested user configuration is preserved by the revised volatile-field filter.
- Selected UI deletions have an explicit flag and a working basic CLI path.
- Dashboard metadata update/readback has implementation and regression coverage.
- Core ConfigMap generation and synchronization validation now exist.
- Tagged core YAML has JSON serialization support.
- Plans now check source payloads, logical instance labels, baseline markers,
  age, and HA version in several previously missing cases.

These observations close the corresponding narrow reproductions, not the full
plan's end-to-end acceptance requirements.

## Remaining findings

### F1. P1: every new HA deployment job uses invalid CLI argument ordering

Location: `.gitlab-ci.yml:583-593` and
`scripts/home_assistant/__main__.py:1103-1120`.

The jobs invoke `... plan --instance homelab-01`, and similarly invoke `diff`,
`apply`, and `verify`. `--instance` is defined on the root parser, not these
subparsers. Parsing the exact plan arguments exits 2 before any work. The new
production deployment path therefore cannot run successfully as committed.

Fix the commands or consistently support common options after subcommands. Add
tests parsing the actual CI invocations. Also pass the generated immutable plan
to `apply --plan-file`; the current job discards it and generates another plan.
Test the full job sequence with fake transports and an existing baseline before
claiming the protected deployment path works.

### F2. P1: diff, adoption, and planning never read the shared baseline

Location: `scripts/home_assistant/__main__.py:386,466,743`.

Only apply/verify/revert construct `Planner(..., client=client)`. The three
entrypoints agents use to inspect and adopt changes still construct it without
a client, so they only read the local cache. A fresh checkout with an existing
shared baseline classifies a simple UI-only modification as a conflict. The
reproduction supplied B in the mock cluster, G equal to B, and L changed; selected
`diff` returned 2 with `conflict` instead of `experiment`.

This also prevents a fresh CI checkout from planning an ordinary Git-only update
to an existing live resource. Fix all readers to use the same authoritative state
backend and distinguish unavailable state from uninitialized state. Test the
whole capture/diff/adopt/plan/apply chain from a second checkout, not only that
`verify` can write a mock ConfigMap.

### F3. P1: adoption still overwrites committed Git-only changes

Location: `scripts/home_assistant/__main__.py:500-508,591-593,629-636`.

Adoption rejects `CONFLICT` and `UNKNOWN`, but accepts `GIT_CHANGE`. If a desired
change has been committed while live HA still equals B, the dirty-file check
passes and adoption replaces G with the old live definition. `--all` includes
these resources too. This can silently undo an agent-authored change while the
user is asking to adopt unrelated UI experiments.

Reproduction used a real temporary Git repository with a clean committed target,
local baseline alias "baseline", Git alias "committed Git change", and live alias
"baseline". Selected adoption returned 0 and reset the Git file to "baseline".

Only UI experiment classifications should produce ordinary adoption writes or
deletions. Skip or explicitly reject Git-only changes; discarding accepted source
requires separate explicit intent. Keep converged/clean resources as no-ops, and
test mixed `--all` selections containing both UI and Git changes.

### F4. P1: the new lock can still grant ownership to concurrent callers

Location: `scripts/home_assistant/planner.py:46-48,99-134`.

`O_EXCL` creates the file before its JSON body is written. A concurrent reader
can see that empty file, treat it as corrupt, unlink it, and acquire a replacement.
The first writer then finishes writing to its unlinked file and also returns
success. Renewal rewrites JSON in place, creating another partial-read window.

A coordinated two-thread reproduction paused caller A after its exclusive open
but before writing JSON. Caller B acquired the same lock successfully, then A
resumed and also returned success. Separate checkouts additionally have entirely
separate lock paths; both acquired the same instance lock. The HA CI jobs have no
instance `resource_group` either.

Use a real atomic ownership mechanism on a shared backend with conditional
renewal/release. Never interpret a partially written lock as permission to remove
a live owner's lock. Test actual concurrent acquisition and takeover, including
different checkouts; a sequential acquire-then-reject test does not cover this.
Retain the documented UI editing pause because deployment locks do not lock HA UI.

### F5. P1: failed authoritative checkpoint operations are reported as success

Location: `scripts/home_assistant/client.py:646-695` and
`scripts/home_assistant/planner.py:53-87`.

Cluster reads swallow errors and return None; Planner then silently falls back to
local state. Cluster writes ignore the subprocess return code and exceptions,
and Planner also catches failures after saving locally. A rejected/missing shared
checkpoint can therefore look like a completed deployment while another checkout
continues using an older baseline.

Reproduction made `save_cluster_baseline` raise a write-rejected error. `verify`
returned 0 with `verified`, although no shared record existed.

Require successful authoritative persistence and readback before reporting the
checkpoint complete. Surface authentication, network, and write errors distinctly
from explicit not-found/bootstrap. Do not silently promote local cache to authority.
Use revision-conditional writes so concurrent checkpoints cannot replace each other.

### F6. P1: per-resource collection failures still become apparent deletions

Location: `scripts/home_assistant/client.py:349-362` and
`scripts/home_assistant/adapters/automation.py:30-57`.

The new aggregate error propagation is useful, but automation fallback still
catches every individual `get_automation` error and skips the resource. The adapter
also suppresses errors during its registry pass. With filesystem reads unavailable,
a listed automation whose configuration GET times out still produces an empty
successful list, so downstream comparison can infer a UI deletion.

Reproduction returned a registry entry for `automation.review`, raised a timeout
from its config getter, and disabled the file read. `list_automations()` returned
`[]` rather than an error. Test the actual collector/adapter chain; manually
injecting `automation/all` into the comparison test misses this failure.

Also, `capture` still returns 0/`captured` when an adapter fails and stores an
error object beside the other resources. Report incomplete status with a nonzero
exit code. Treat wrong-shaped files/responses as invalid, not empty collections.

### F7. P1: ordinary plaintext API keys bypass the new preflight scanner

Location: `scripts/home_assistant/canonical.py:277-304`.

Sensitive dictionary-key detection omits `api_key`. The inline-text regex does
not inspect a mapping as a serialized key/value expression, and generic API keys
do not necessarily start with `sk-` or look like JWTs. An automation action with
`data.api_key: synthetic-example-key-1234` was adopted successfully and persisted
the literal into the source YAML.

Add structured sensitive-field handling and adapter export policies for credentials,
not just token-format patterns. Cover API keys, authorization fields, nested data,
and URL parameters. Rejected payloads must not reach source, capture, plan artifacts,
or logs. The original password test passes but does not establish this contract.

### F8. P1: baseline identity and acceptance are still not maintained

Location: `scripts/home_assistant/__main__.py:965-986` and
`scripts/home_assistant/planner.py:270-296,460-474`.

`verify` initializes `content_hash` to an empty string and never recomputes it.
Apply copies a marker/hash into the baseline and also does not update it when
resources change. Consequently the new baseline-hash check can compare unchanged
markers across different accepted contents. Verification also publishes the local
source into shared state without proving that source was committed or published.

Reproduction verified two different live/source definitions; both shared records
had `content_hash == ""`. The second uncommitted definition was accepted into
the shared baseline with a success result.

Compute and validate a real baseline content/revision identity on every update.
Bind checkpointing to the published source artifact or explicitly authorized
bootstrap, rather than making ordinary local verification an acceptance operation.
Validate source/target/baseline under the shared lock and update the checkpoint
conditionally. Test stale plans after a different resource advances the baseline.

## Validation and limits

`nix develop ./flake -c bash scripts/checks/home-assistant.sh` passed: formatting,
lint, Pyright, all 45 tests, desired-source validation, and YAML lint.

Additional isolated reproductions confirmed every remaining finding above:

| Scenario | Observed result |
| --- | --- |
| Exact CI plan arguments | Parser exits 2 |
| Fresh checkout with cluster baseline and UI-only edit | Conflict, exit 2 |
| Adopt a clean committed Git-only change | Git reset to live, exit 0 |
| Concurrent same-checkout lock acquisition | Both callers acquire |
| Two checkouts acquire same-instance locks | Both acquire |
| Cluster checkpoint write raises | Verification still returns 0 |
| Individual automation GET times out | Collection returns empty list |
| Core collector fails during capture | Returns 0/`captured` |
| Nested action API key | Literal persists to Git source, exit 0 |
| Different verified baselines | Same empty content hash |
| Local uncommitted source matches live | Published into shared checkpoint |

No production writes or deployment were attempted. Full offline repository checks,
real isolated HA compatibility, production restart persistence, and recovery
rehearsals were not established by this review. The next repair should add tests
for the complete command and transport paths above, then demonstrate both user
workflows from fresh checkouts against the supported isolated HA version.
