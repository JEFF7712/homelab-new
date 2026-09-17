# Jarvis voice runbook

## Scope and ownership

Jarvis is the Homelab voice assistant. The container stack is owned by Flux
(`gitops/voice/`, deployed via `gitops/clusters/homelab-01/voice.yaml`). The
kiosk face is owned by NixOS (`flake/hosts/homelab-05/default.nix` plus
`flake/modules/kiosk.nix`) and served as HA local media
(`home-assistant/www/jarvis/`). The HA-side routing (Wyoming servers, Assist
pipeline, conversation agent, exposed entities) is UI-managed config-entry
state, which this repo treats as `observe-only`; the required settings are
recorded here so a rebuild restores them exactly.

## Signal chain

Microphone on `homelab-05` (`HyperX QuadCast S` via Pipewire) -> satellite
container (`linux-voice-assistant`, wake word `hey_jarvis.tflite`, port 6053)
-> Home Assistant on `homelab-03` -> STT/TTS/LLM on `homelab-04`
(`wyoming-whisper` 10300, `wyoming-piper` 10200, `ollama` 11434) -> audio back
to the `homelab-05` speaker -> face state via the HA websocket.

## Canonical entity IDs

Do not rename these without updating `home-assistant/www/jarvis/config.json`,
`home-assistant/www/jarvis/app.js` defaults, and
`home-assistant/dashboards/lovelace-jarvis.yaml` together:

- `assist_satellite.homelab_05_satellite_assist_satellite`
- `switch.homelab_05_satellite_mute`
- `media_player.homelab_05_satellite_media_player`
- `switch.homelab_05_satellite_thinking_sound`
- `number.homelab_05_satellite_mic_volume`
- `select.homelab_05_satellite_wake_word`

`CLIENT_NAME` in `gitops/voice/satellite.yaml` must stay
`Homelab 05 Satellite`. HA derives the entity-ID prefix from it; renaming the
client renames every entity above and breaks the face, the dashboard, and any
automation referencing them.

## HA wiring checklist (UI, observe-only)

1. Wyoming integrations pointing at the in-cluster services:
   `voice-satellite.voice:6053` is the satellite link from HA;
   `wyoming-whisper.voice:10300` for STT and `wyoming-piper.voice:10200`
   for TTS.
2. One Assist pipeline with Whisper `base.en` as STT, Piper
   `en_GB-alan-medium` as TTS, and the Ollama conversation agent
   (`http://ollama.voice:11434`) as the brain, with model `qwen2.5:3b`
   selected. Set it as the preferred pipeline and select it on the
   satellite device.
   The Jarvis conversation subentry prompt carries the room semantics:
   downstairs means Living Room plus Kitchen, light commands with no room
   default to all downstairs lights, and light color changes default to
   Govee light bulbs. Output is tuned for concise spoken acknowledgments.
   The context window must be set to `num_ctx: 8192` (at 2048 Ollama truncates
   the 3.5k+ token prompt and tool schemas) and `llm_hass_api` set to
   `assist` only (omitting SmartHQ saves ~1.2k tokens of unused tool schemas).
   The prompt is UI-managed config-entry state; the `light.downstairs_lights`
   group in `home-assistant/core/configuration.yaml` is its deterministic backup.
3. Expose exactly the entities Jarvis may control (lights, switches, climate
   in `home-assistant/core/configuration.yaml` groups, plus scenes and the
   shopping list) to Assist. Unexposed entities are invisible to voice
   commands. Exposure audit 2026-09-17: 59 exposed down to 37. Deliberately
   unexposed: all AC alert internals, Bambu bed/nozzle thermometers, AC
   RSSI/energy-counter sensors, browser_mod screen and player, the AC
   temperature-units selector, the four adaptive-lighting control switches
   (name-collision risk with "turn off all lights"), and
   `switch.zigbee2mqtt_bridge_permit_join` (voice must never open Zigbee
   pairing). Kept AC ambient-temperature, power, and mode sensors for
   "how warm / is it on" queries. When adding devices, expose only the
   control entity, never diagnostic sensors.
4. The kiosk bypass in `configuration.yaml` `trusted_networks` must keep
   `10.0.30.15/32` so the face websocket authenticates without a prompt.
   The long-lived token remains the fallback and is stored only in the kiosk
   browser profile, never in Git.

## Pinned images

Voice images are pinned by digest in their manifests (repo convention, with the
source tag kept in a trailing comment). The current pins and their upstream
sources for refresh:

| Deployment | Image | Pin | Refresh |
| --- | --- | --- | --- |
| satellite | `ghcr.io/ohf-voice/linux-voice-assistant` | `1.1.1` | tags list on GHCR; `latest` floats past releases, so pin the newest stable tag, not `latest` |
| whisper | `docker.io/rhasspy/wyoming-whisper` | `3.8.1` | Docker Hub tags, newest `3.x` |
| piper | `docker.io/rhasspy/wyoming-piper` | `2.5.2` | Docker Hub tags, newest non-`omnivoice` `2.x` |
| ollama | `docker.io/ollama/ollama` | `0.34.1` | Docker Hub tags, newest stable (skip `-rc`) |

Refresh with `just check-changed` and `just check` before handoff. Bumping the
satellite past `1.1.1` re-derives entity behavior; re-verify the canonical IDs
above after any satellite bump.

## Model contract

The served model is declared in `gitops/voice/ollama.yaml` as the
`ollama-qwen2-5-3b-ready` Job: an init step pulls `qwen2.5:3b` (1.9 GB, fits
the 4 GB T1000 with context headroom), then a warmup step runs one short
inference so the model is resident in VRAM before the first user turn. The
pull is idempotent: reruns skip cached layers. `OLLAMA_KEEP_ALIVE=-1` keeps
the model resident after first load.

Limits of this scheme: `ollama pull` resolves tags, not digests, so the tag
is mutable upstream. If a refresh misbehaves, the previous model blobs remain
on disk until replaced.

To switch models: change the pull and warmup args and rename the Job (Job
specs are immutable, so a new name is required), update the HA conversation
agent to the same model name, and update the canonical-model references in
this runbook.

## Model storage

All three model caches live on `homelab-04` local NVMe at
`/persist/voice-models/{ollama,whisper,piper}` via `hostPath`. This is
deliberate: every consumer is already pinned to `homelab-04`, local disk
removes the NAS as a voice dependency and loads multi-GB models off NVMe
instead of 1 GbE NFS. The caches are fully re-derivable (re-pull on empty
dir), so they are not backed up. The orphaned NFS directories from the
retired PVCs can be reclaimed on the NAS by hand.

## Latency notes

- LLM first-token time on the 4 GB T1000 dominates a turn. Keep
  `OLLAMA_KEEP_ALIVE=-1` so the model stays loaded, and prefer a small model
  that fits VRAM without spilling to system RAM. Check residency with the
  Ollama `/api/ps` endpoint; a model larger than VRAM spills to system RAM
  and every turn pays for it.
- Whisper runs `turbo` (large-v3-turbo, ~800 MB) on `homelab-04` CPU with
  `--beam-size 1` (greedy decoding; the pinned 3.8.1 defaults to beam 5 on
  x86) and a 6-core cap. Turbo matches large-v3 accuracy near base-model
  speed, and fixed `--language en` skips auto-detect. `distil-small.en` was
  rejected: upstream notes it is damaged by missing prompt conditioning.
  Further options, in order of invasiveness: drop to `tiny.en`, or move STT
  to GPU at the expense of Ollama headroom (4 GB VRAM is already spoken for
  by `qwen2.5:3b`).
- Piper is sub-second at steady state but re-downloads its voice on every pod
  restart unless its model cache persists. Voices persist on the
  `piper-voices` PVC (`gitops/voice/storage.yaml`); do not revert that volume
  to `emptyDir`.
- Model pulls (Whisper, Piper, Ollama) hit the network only on first-ever
  start; after that they load off local NVMe. The ready Job warms VRAM on
  initial deploy and model switches (completed Jobs do not rerun). After a
  node reboot, the first turn reloads the model off NVMe in seconds and
  `KEEP_ALIVE=-1` holds it from there; the startup probes gate exactly this.
- The face renders heavy glow/blur CSS in Chromium on the T600. If state
  transitions visibly jank, reduce the blur radii in
  `home-assistant/www/jarvis/style.css` before suspecting the pipeline.

## Observability

`gitops/voice/exporter.yaml` runs `jarvis-exporter`, a dependency-free
Python exporter that holds the HA websocket, tracks satellite state
transitions per turn, and counts `call_service` bus events seen while the
satellite is processing. Scraped via the `jarvis-exporter` ServiceMonitor
into the kube-prometheus-stack Prometheus; visualized by the Jarvis Voice
Grafana dashboard (`grafana-dashboard-jarvis` ConfigMap).

Metrics and their exact semantics:

- `jarvis_requests_total{satellite}`: turns that reached idle through responding.
- `jarvis_stt_latency_seconds{satellite}`: listening-phase duration, which is
  utterance time plus transcription. It is not pure STT compute; compare
  turns, not against compute budgets.
- `jarvis_llm_latency_seconds{satellite}`: processing-phase duration.
- `jarvis_tts_latency_seconds{satellite}`: responding-phase duration.
- `jarvis_tool_calls_total{satellite}`: service calls on the shared bus
  during processing. Adjacent automations firing mid-turn can inflate this.
- `jarvis_failed_requests_total{satellite,stage}`: turns abandoned from
  listening or processing without ever responding.
- `jarvis_requests_by_room_total{room}`: completed turns attributed to the
  area of the first targeted entity, else `unknown`.
- `jarvis_exporter_ha_connected`: 1 while the websocket is authenticated.

The exporter needs a Home Assistant long-lived token in the GitLab project
variable `JARVIS_EXPORTER_HA_TOKEN` (consumed via the `gitlab-project`
ClusterSecretStore). Without it the exporter still serves `/metrics` with
`connected=0`, and the dashboard shows no turns. Exporter logic is covered
by `tests/test_jarvis_exporter.py`, which executes the exact script embedded
in the ConfigMap.

## Failure symptoms

- Face stuck on `CONNECT SATELLITE` prompt: kiosk token missing and
  `trusted_networks` bypass not matching. Check the bypass and re-enter the
  long-lived token once.
- Face shows IDLE but never LISTENING: satellite pod not ready or HA Wyoming
  entry pointing at the wrong host. `just status cluster` plus the satellite
  pod events; confirm the HA Wyoming host is `voice-satellite.voice`.
- First turn after deploy is very slow, later turns fine: model cold start.
  Check probe status on whisper/piper/ollama before tuning anything.
- Every turn slow: Ollama model spilling past 4 GB VRAM, or Whisper CPU
  throttled. Check `ollama ps` output model size and pod resource usage.
- Face state frozen while voice works: HA websocket broken in
  `app.js`; use keys 1-5 on the kiosk keyboard to confirm the face itself
  still cycles states.
