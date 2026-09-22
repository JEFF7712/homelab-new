# Jarvis Audit Remediation Plan

Status: in progress (8 open checkboxes as of 2026-09-22; deployment-window evidence pending).

**Goal:** Repair audit findings 1, 2, 4, and 5 without changing the command trust boundary or silently mutating UI-managed Home Assistant state.

**Scope:** Exporter connectivity, Jev safety evidence, runbook accuracy, and Chatterbox runtime behavior. Stable gateway and network-policy work is owned separately and must be integrated before live verification.

## Task 1: Restore trustworthy exporter telemetry

**Files:** `gitops/voice/exporter.yaml`, `tests/test_jarvis_exporter.py`, `gitops/observability/grafana/dashboard-jarvis.yaml`

- [x] Reproduce the one-minute disconnect with a protocol test that sends websocket ping, pong, close, fragmented, and idle frames.
- [x] Replace the handwritten websocket transport with a maintained client already available in the pinned runtime, or fully implement RFC 6455 ping/pong and close handling.
- [x] Separate process health from HA connectivity: liveness proves the exporter loop runs, readiness requires authenticated subscription state.
- [x] Add reconnect, authentication-failure, last-event-age, and subscription-state metrics.
- [x] Preserve counters across reconnects and prove one HA event is counted once after resubscription.
- [x] Add a Prometheus alert for disconnected or stale telemetry.
- [ ] Verify locally with unit tests, then live with `jarvis_exporter_ha_connected == 1` for at least 35 minutes and a real completed voice turn visible exactly once.

## Task 2: Turn Jev evaluation into a deployment gate

**Files:** `tests/jev_decision_corpus.yaml`, `tests/test_jev_decision_bench.py`, `scripts/record_jev_decisions.py`, `.gitlab-ci.yml`, `docs/runbooks/jarvis-voice.md`

- [x] Classify every recorded false action by failure mode: target, action, negation, correction, compound request, numeric value, or STT corruption.
- [x] Add each failure as an immutable regression case with the expected zero-action behavior.
- [x] Define separate release gates for false-action rate, execute-field accuracy, route accuracy, calibration error, and latency.
- [x] Require zero false actions for restricted and adversarial categories. Do not trade safety for aggregate route accuracy.
- [x] Expand deterministic local sentences or L0 parsing for common safe paraphrases before changing model thresholds.
- [x] Keep the current 0.95 control and 0.98 climate thresholds until a newly recorded corpus proves a safer change.
- [x] Make CI fail when a new model fixture or router change regresses the gates.
- [ ] Run the text corpus live only during an authorized window because local cases execute device actions.

## Task 3: Make the runbook generated-state aware

**Files:** `docs/runbooks/jarvis-voice.md`, `scripts/voice_topology.py`, `tests/test_voice_topology.py`, `justfile`

- [x] Define a non-secret topology report containing available deployments, desired replicas, gateway preference order, Service targets, live endpoints, HA pipeline engines, and health.
- [x] Generate the desired-state portion from manifests and the live portion from read-only Kubernetes and HA config-entry inspection.
- [x] Mark missing evidence as unknown. Never infer deletion or health from an incomplete read.
- [x] Add `just voice-topology` and a drift check that compares runbook invariants with desired state.
- [x] Rewrite the signal chain around stable STT and TTS gateways, with backend choice and fallback shown separately.
- [x] Document recovery for gateway loss, primary backend loss, all-backend loss, and HA pipeline drift.
- [ ] Verify the generated report against the deployed cluster after the gateway rollout.

## Task 4: Make Chatterbox failure observable and recoverable

**Files:** `gitops/voice/chatterbox.yaml`, `gitops/voice/chatterbox-bridge/server.py`, `tests/test_chatterbox_bridge.py`, gateway tests and dashboards

- [x] Redirect Hugging Face, Torch, Triton, and XDG caches to explicit writable paths and assert startup produces no cache-permission warning.
- [x] Decide and document the watermark policy. Fail startup if watermarking is required but unavailable; otherwise export an explicit unwatermarked-audio gauge.
- [x] Replace synthetic silence on synthesis exceptions with an explicit failed stream that the TTS gateway can detect.
- [x] Buffer only the small TTS request so the gateway can retry Piper once without replaying partial audio.
- [x] Export synthesis success, failure, time to first audio, generated-audio duration, real-time factor, and fallback counters.
- [x] Add a fault-injection test where Chatterbox fails before audio, Piper succeeds, and the client receives exactly one valid audio stream.
- [x] Add a second test proving failure after the first audio chunk never splices Piper audio into an existing response.
- [ ] Verify the cloned voice, GPU residency, cache behavior, and automatic Piper fallback live before removing the manual recovery note.

## Completion gate

- [ ] Targeted tests and `just check-changed` pass.
- [ ] `just fmt-check` passes for task-owned files.
- [ ] Final diff contains no recordings, credentials, generated model data, or unrelated dashboard and CAD changes.
- [ ] Deployment is reviewed separately. After authorization, reconcile Flux and verify runtime state, metrics, fallback behavior, and HA pipeline identity.

Offline implementation status: the affected unit tests, GitOps render, YAML
validation, Ruff checks, and `just fmt-check` pass. `just check-changed` cannot
select a scoped check in the current dirty checkout because unrelated WIP
paths have no maintained validation mapping. Live exporter duration, deployed
topology, cloned voice, GPU residency, and fallback verification remain
deployment-window evidence.
