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

Microphone on `homelab-05` (`HyperX QuadCast S` via Pipewire, pinned with
top priority 2500 in WirePlumber) -> satellite container (`linux-voice-assistant`,
wake word `hey_jarvis.tflite`, port 6053, device substring match `QuadCast`)
-> Home Assistant on `homelab-03` -> Voice-ID proxy on `homelab-04` (port 10300)
-> Whisper STT (`wyoming-whisper` localhost:10301) -> transcript with speaker tag
`speaker <Name>` -> TTS/LLM on `homelab-04` (`wyoming-piper` 10200, `ollama` 11434)
-> audio back to the `homelab-05` soundbar (HDMI-A-2 with continuous video clocking daemon,
prioritized at 2000 in WirePlumber) -> face state via the HA websocket.

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
   default to all downstairs lights, light color changes default to
   Govee light bulbs, and music/artist/playlist requests explicitly call
   `script.jarvis_play_media` (`media_content_type='music'`). The canonical
   prompt text is recorded below ("Conversation prompt"); the live copy is
   UI-managed config-entry state, so keep the two in sync on any edit.
   Required conversation-agent settings, in priority order:
   - `Prefer handling commands locally`: ON. Built-in intents answer basic
     light, scene, and state commands without waking Qwen. Qwen is the
     fallback for ambiguous, multi-step, music, and general questions.
   - `Max history messages`: 4. Old turns hurt a 3B model more than they
     help; follow-ups inside one continued conversation still work.
   - `num_ctx`: 8192 (at 2048 Ollama truncates the 3.5k+ token prompt and
     tool schemas). The 8k window is headroom, not a target; keep pruning
     prompt and exposures instead of filling it.
   - `llm_hass_api`: `assist` only (omitting SmartHQ saves ~1.2k tokens of
     unused tool schemas).
   The `light.downstairs_lights` group in
   `home-assistant/core/configuration.yaml` is the deterministic backup for
   the room semantics.
3. Terse local replies are enforced in Git, not in the LLM prompt: a local
   command never reaches Ollama, so the prompt cannot shorten it.
   `home-assistant/custom_sentences/en/jarvis_terse.yaml` overrides the
   built-in action-intent responses (`HassTurnOn`, `HassTurnOff`,
   `HassToggle`, `HassLightSet`) with `Done.` It deploys via the
   `home-assistant-config` ConfigMap
   (`scripts/home_assistant/adapters/core.py` renders every
   `home-assistant/custom_sentences/<lang>/*.yaml` into it under dotted
   `<lang>.<name>` keys, since ConfigMap keys cannot contain slashes, and
   the HA initContainer splits them back into `/config/custom_sentences/`
   on boot). State queries keep their
   dynamic built-in responses; do not override them with static text.
   Extend the override file only after inspecting Assist traces for the
   next most common intents.
   Signature colors live one layer up: the Ollama `HassLightSet` tool
   accepts color *names* only (validated by `color_name_to_rgb`), so the
   LLM can never emit exact hex and "pink" always lands on CSS pink
   (255, 192, 203). `home-assistant/custom_sentences/en/jarvis_colors.yaml`
   maps phrases like "neon pink" / "hot pink" onto room and plug targets,
   and `intent_script.JarvisSignatureColor` in `configuration.yaml` fires
   `light.turn_on` with hardcoded `rgb_color: [255, 16, 240]`, replying
   `Done.` To add a color: append its phrases to the `jarvis_color` list
   and add a `choose` branch on `{{ jarvis_color }}` in the intent script.
   These requests resolve in the local intent engine, never reaching Qwen.
4. Expose 15 to 25 conceptual controls to the Ollama agent, not every raw
   entity. Prefer groups (`light.downstairs_lights`), named lamps actually
   mentioned by voice, climate controls, scenes, music, and the shopping
   list. Diagnostic and status sensors stay available to deterministic local
   queries but do not go into Qwen's tool schema. Exposure audit 2026-09-17:
   59 down to 37, then cut to 19 managed controls (5 light groups, 4
   plug/sign singles, thermostat plus 2 AC sensors, 3 shared scenes,
   `script.jarvis_play_media`, shopping list, satellite media player,
   stairs light). Dropped: 7 Govee/Roku singles covered by their groups,
   6 bedroom scenes, AC power sensor. Four unregistered entities (sun,
   zone, `sensor.ha_latest_version`, `conversation.home_assistant`) have no
   exposure flag and stay visible; negligible cost.
   Deliberately unexposed: all AC alert internals, Bambu bed/nozzle
   thermometers, AC RSSI/energy-counter sensors, browser_mod screen and
   player, the AC temperature-units selector, the four adaptive-lighting
   control switches (name-collision risk with "turn off all lights"), and
   `switch.zigbee2mqtt_bridge_permit_join` (voice must never open Zigbee
   pairing). Kept AC ambient-temperature, power, and mode sensors for
   "how warm / is it on" queries. When adding devices, expose only the
   control entity, never diagnostic sensors.
5. The kiosk bypass in `configuration.yaml` `trusted_networks` must keep
   `10.0.30.15/32` so the face websocket authenticates without a prompt.
   The long-lived token remains the fallback and is stored only in the kiosk
   browser profile, never in Git.
6. Satellite audio and VAD tuning (on device `Homelab 05 Satellite`):
   - `select.homelab_05_satellite_finished_speaking_detection`: set to `aggressive`
     (0.25s silence detection vs. 0.7s default).
   - `select.homelab_05_satellite_mic_noise_suppression`: set to `High` (level 3).
   - `number.homelab_05_satellite_mic_volume`: set to `75.0`. At 100% gain, the
     QuadCast S condenser mic saturates room ambient noise, causing Silero VAD to
     treat background hum as ongoing speech until hitting the 10-second STT
     safety timeout. Lowering to 75% with High noise suppression detects the end
     of speech immediately.
7. Music playback (Music Assistant & providers):
   - `script.jarvis_play_media` is exposed to Assist to handle music requests.
   - `home-assistant/automations/jarvis_voice_music_playback.yaml` catches
     play commands before the LLM and routes by trigger id: artist phrasings
     ("play some X", "put on X") resolve the artist via search, then start
     an endless artist mix (`music_assistant.play_media`, `radio_mode: true`)
     so playback continues past the first track; song, album, and playlist
     phrasings keep narrower lookups.
   - Stopping is deterministic and local: `home-assistant/automations/jarvis_music_stop.yaml`
     pauses the satellite speaker on "turn off [the] music" / "turn [the] music
     off" (built-in intents already cover "stop the music"). Never route music
     stop through the LLM: on 2026-09-18 "turn off the music" fell to Qwen and
     died on a poisoned chat log while "stop the music" paused in 13 ms.
   - Platform parameter supports `spotify` (default) and `youtube_music` (`ytmusic`).
   - Music Assistant runs on `homelab-05` host network
     (`gitops/music-assistant/server.yaml`) and routes audio to the satellite speaker.
   - YouTube Music streaming requires a Proof-of-Origin (PO) token server; the
     `pot-provider` companion container (`brainicism/bgutil-ytdlp-pot-provider:1.2.1`)
     runs on `homelab-05` at `http://127.0.0.1:4416`.

## Conversation prompt (canonical)

Paste this verbatim into the Jarvis conversation subentry. Keep this copy
and the live copy in sync; this file is the reviewable source.

```text
You are Jarvis, the voice assistant for this Home Assistant instance.

Your primary job is to understand the user's request, perform the requested
Home Assistant action when appropriate, and respond with as few words as
possible.

RESPONSE STYLE

Voice responses must be extremely concise.

Respond in English.

For a successfully completed action, respond exactly:

Done.

Do not describe the action you just performed unless the user asks.

Bad: "I've turned off all of the lights downstairs for you."
Good: "Done."

For a successfully completed multi-step action, also respond: Done.

For a simple factual question about the home, answer with only the requested
information. Examples: "What's the temperature downstairs?" -> "72 degrees."
"Are the kitchen lights on?" -> "Yes." "What's playing?" ->
"Nights by Frank Ocean."

For general questions, answer concisely. Prefer one or two sentences unless
the user explicitly asks for detail.

Never add filler such as: "Certainly." "Of course." "Sure thing."
"I'd be happy to." "Here you go." "Let me check." "Anything else?"

Do not repeat the user's request back to them.

SPEAKER RECOGNITION

The user input begins with `speaker <Name>` (e.g. `speaker Rupan` or
`speaker Sam`) when their voice is recognized.
When the user asks "who am I", "who is speaking", or what their name is,
identify them directly and concisely: "You are Rupan." or "You are Sam." If no
speaker tag is present or voice is unknown, reply: "I don't recognize your voice."

ACTION RULES

When the user requests an action: perform the action first, wait for the
tool result, and if it succeeds say "Done." Never claim success unless the
tool confirms it. If an action fails, state the problem briefly
("Couldn't reach the bedroom lights.", "Spotify is unavailable."). If only
part of a request succeeds, say what failed in one short sentence.

Do not explain Home Assistant internals, entity IDs, service names, tool
names, or implementation details unless explicitly asked.

Do not ask for confirmation for ordinary reversible actions such as lights,
music, scenes, climate adjustments, or volume changes.

If the request is genuinely ambiguous and acting could produce an incorrect
result, ask one short clarification question.

ROOM SEMANTICS

"Downstairs" means the Living Room and Kitchen. When the user gives a light
command without specifying a room, default to all downstairs lights unless
conversational context clearly establishes another room. When the user asks
to change a light color without naming a specific light, default to the
Govee light bulbs in the relevant room. Use Home Assistant areas, groups,
and entities rather than guessing device names.

MUSIC

For music, artist, album, song, or playlist requests, use
`script.jarvis_play_media`. When a `speaker <Name>` tag is present, default
platform to 'spotify' for Rupan and 'youtube_music' for Sam, passing
speaker='Rupan' or speaker='Sam'. If the user explicitly requests another
platform (e.g. "on youtube music" or "on spotify"), respect the user's explicit
choice. A bare artist name or "play some X" means the artist: pass
media_content_type='artist' and the script starts an endless artist mix.
Never ask which album or song; just play. Specific songs use 'music', albums
'album', playlists 'playlist'. After successful playback begins, say: Done,
<Name>. (or Done. if speaker is unverified).

CONTEXT

Treat the current conversation as temporary. Use recent conversation context
only to resolve natural follow-ups such as "turn it off", "make it
brighter", "what about upstairs?", "yes", or "no". Do not invent context
that is not present. Do not allow an unrelated earlier request to influence
a new request.

PRONOUN SAFETY

Never perform an action based on "it", "them", "that", "those", "there",
or similar references unless the referenced object is unambiguous from
the current conversation.

If this is the first message in a conversation, such pronouns never have
an antecedent.

Ask a short clarification question instead.

KNOWLEDGE AND HOME STATE

For questions about the current state of the home, use Home Assistant state
information rather than guessing. Never fabricate temperatures, device
states, media playback, light states, presence, or sensor readings. If the
required information is unavailable, say so briefly.

BEHAVIOR

Be precise, quiet, and action-oriented. The ideal interaction is: user gives
command, Jarvis performs it, Jarvis says "Done." Only speak more when the
user actually needs information.
```

## Conversation lifetime

Every new wake-word activation starts a new conversation. Do not persist
context across separate "Hey Jarvis" invocations: a bare "turn them back
on" twenty minutes later must ask for clarification, never resolve "them"
from a stale turn. Multi-turn follow-ups ("Yes.", "make it brighter") work
only inside a continued satellite conversation
(`assist_satellite.start_conversation`). Never restart Ollama or clear its
model cache on wake; `OLLAMA_KEEP_ALIVE=-1`, the Q8 KV cache, and the warmup
Job stay as they are. Conversation state and model residency are separate.

## Self-talk loop defenses

Two layers against the 11:12-11:31 feedback loop (soundbar TTS re-entering
the QuadCast, Whisper hallucinating fragments like `Stu.` / `Control.` /
`Govee, Govee, ...`, every turn continuing the conversation and speaking
again). Layer 1 is live as of 2026-09-18; layer 2 is implemented, unit-tested,
and embedded in `gitops/voice/voice-id.yaml`, pending a push for Flux to roll
it to the whisper pod:

1. Muting the satellite during TTS was tried via
   `home-assistant/automations/jarvis_satellite_tts_mic_mute.yaml` (mute on
   `responding`, unmute 300 ms after `idle`) and FAILED on 2026-09-18: LVA's
   mute switch is a user shut-up control, not a capture gate. Engaging it
   runs `tts_player.stop()` (killing the in-flight reply ~100-250 ms in) and
   plays mute/unmute chimes through the same single mpv instance, so every
   reply was truncated and chimed over. It also mistimes: HA reports `idle`
   at pipeline end while the mp3 keeps playing. The file stays in Git
   disabled (`initial_state: false`) as a record; do not re-enable without
   a satellite build whose mute path skips stop and chimes. Barge-in during
   TTS remains unavailable by design (single mpv, no duplex path).
2. Transcript sanity guard in `scripts/voice_id/proxy.py`
   (`is_garbage_transcript`, unit-tested in
   `tests/test_transcript_guard.py`, embedded into `gitops/voice/voice-id.yaml`
   via the enrollment procedure below): drops empty transcripts, a single
   token repeated 3+ times, and a tight denylist of observed hallucinations.
   Dropped transcripts are forwarded as empty text, which HA abandons
   silently. Never denylist bare `Hey Jarvis.` (keeps the lone-wake-word
   acknowledgement) or `Stop.` (the loop escape hatch).

Deliberately not done: semantic similarity against the last TTS text needs
a TTS-text feed into the proxy that does not exist yet; the mute gate
already covers the window where semantic echo occurs. Revisit if echo
turns survive both layers.

## Satellite health

`gitops/voice/satellite.yaml` gates readiness on a TCP probe against port
6053, so the pod leaves the rotation when the Wyoming server stops
accepting connections even if the process is still alive. Startup and
liveness keep the `pgrep -f linux_voice_assistant` exec checks. The HA-level
`jarvis_satellite_watchdog.yaml` automation stays as the higher-level check
for HA losing the satellite.

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
| pot-provider | `docker.io/brainicism/bgutil-ytdlp-pot-provider` | `1.2.1` | Docker Hub tags, newest stable |

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
- `gitops/voice/ollama.yaml` enables `OLLAMA_FLASH_ATTENTION: "true"` and
  `OLLAMA_KV_CACHE_TYPE: "q8_0"`. On Turing (Compute 7.5), flash attention
  accelerates attention computation while Q8_0 cuts the KV cache memory footprint
  in half (~750 MB savings at 8k context), preventing CUDA memory pressure on
  the 4 GB T1000.
- Cold KV prompt evaluation vs. warm turn: Warm turns (hitting cached prompt
  prefixes) take ~0.3–1.0s total. When cold (after model reloads or context resets),
  evaluating the ~3.5k–3.8k token prefix (system prompt, tool schemas, exposed
  entities) takes several seconds. Pruning unneeded entities and tool schemas from
  Assist exposure keeps the prefix lean and directly lowers cold evaluation latency.
- Whisper runs `base.en` (~140 MB) on `homelab-04` CPU with `--beam-size 1`
  and fixed `--language en`. `base.en` completes transcription in ~300ms on
  CPU. `turbo` (large-v3-turbo, ~800 MB) was benchmarked and rejected: without
  GPU acceleration, `turbo` on CPU incurs a ~6.0s transcription delay per turn,
  causing the satellite to appear to stall or listen long after the user stops
  speaking. `base.en` restores sub-second turn responsiveness.
- Piper is sub-second at steady state but re-downloads its voice on every pod
  restart unless its model cache persists. Voices persist on the
  `piper-voices` PVC (`gitops/voice/storage.yaml`); do not revert that volume
  to `emptyDir`.
- Model pulls (Whisper, Piper, Ollama) hit the network only on first-ever
  start; after that they load off local NVMe. The ready Job warms VRAM on
  initial deploy and model switches (completed Jobs do not rerun). After a
  node reboot, the first turn reloads the model off NVMe in seconds and
  `KEEP_ALIVE=-1` holds it from there; the startup probes gate exactly this.
- The face is a Cozmo-style procedural eye engine in
  `home-assistant/www/jarvis/app.js`: expression presets per state (eye
  scale plus upper/lower lids with y/angle/bend, with a right-eye
  asymmetry channel for the confused thinking squint) layered with a
  look assistant (saccades) and a blink assistant (vertical squash),
  all interpolated every animation frame and drawn flat (no glow) on
  `#face-canvas`, with CRT scanlines plus a cached vignette for the
  old-display feel. State colors come from the `#app.state-*` CSS
  variables (`--eye-bg`, `--primary-glow`), overridable per state via
  `face_color_<state>` in `home-assistant/www/jarvis/config.json`.
  Keys 1-6 / click cycle states for visual testing without the pipeline.
  The `music` state replaces the face with a full-screen procedural
  visualizer (56-bar spectrum plus a mirrored waveform ribbon, standard
  blue via `--eye-bg`, flat fills only; no audio tap on the kiosk, so it is
  layered sines rather than real FFT) and shows `Title - Artist` from the
  media player attributes in the status label (`JARVIS // PLAYING //
  <track>`). It shows when the satellite media player is `playing` while
  the satellite itself is idle; mute and the voice states (`listening`,
  `processing`, `responding`) keep priority over it, so music never
  masquerades as speaking.
- The face does no canvas shadows or blur, so face rendering should not
  jank the T600; if it does, suspect the pipeline first.
- Face deploys are self-updating. `home-assistant/www/jarvis/` lives on the
  HA PVC (`/config/www/jarvis/`), not in the ConfigMap, so `ha-apply` does
  not cover it: sync with `kubectl cp` into the home-assistant pod, then
  bump `face_version` in `config.json` and the kiosk `?v=` in
  `flake/hosts/homelab-05/default.nix` to match. The face polls
  `config.json` every 60s and self-navigates to the new version, bypassing
  the kiosk browser cache. No kiosk restart is needed.

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
- `jarvis_turn_speed_class_total{satellite,class}`: completed turns split
  by processing-phase speed, where `class` is `fast` or `slow`. This is a
  latency metric, not a routing label: turns whose processing phase fits
  within `FAST_TURN_MAX_SECONDS` (default `2.0`) count as fast, slower
  turns as slow. Routing ground truth is the `processed_locally` field on
  Assist intent traces, never this series.
- `jarvis_exporter_ha_connected`: 1 while the websocket is authenticated.

The exporter needs a Home Assistant long-lived token in the GitLab project
variable `JARVIS_EXPORTER_HA_TOKEN` (consumed via the `gitlab-project`
ClusterSecretStore). Without it the exporter still serves `/metrics` with
`connected=0`, and the dashboard shows no turns. Exporter logic is covered
by `tests/test_jarvis_exporter.py`, which executes the exact script embedded
in the ConfigMap.

### Eval loop

`tests/jarvis_voice_eval_corpus.yaml` holds 30 to 50 canonical commands with
their expected routing (`local` vs `llm`), target entities, tools, and replies.
`tests/test_jarvis_voice_eval.py` keeps the corpus consistent offline: local
entries must name an intent overridden in
`home-assistant/custom_sentences/en/jarvis_terse.yaml`, reply `Done.`, and
target only entities defined in `home-assistant/core/configuration.yaml` or
`home-assistant/scripts/`.

Whenever the model, prompt, Whisper version, or exposures change, run the
corpus live through `assist_pipeline/run` starting at the `intent` stage
with text input (this exercises real pipeline routing while bypassing only
wake word and STT). Check each `intent-end` event's `processed_locally`
field, the spoken reply, and the exact action taken. A regression is any
local-path case with `processed_locally: false`, any reply longer than the
corpus expects, or any action on an entity outside `targets`. Keep a
smaller acoustic suite (8 to 12 representative commands) for microphone to
Whisper regressions; intent routing and STT are separate concerns.

## Voice-ID speaker recognition

### Architecture and proxy intercept

Home Assistant Assist consumes Wyoming STT events (`audio-start`, `audio-chunk`,
`audio-stop`), but discards raw audio once transcribed. To achieve speaker-aware
routing and personalization without modifying Home Assistant core:

1. A lightweight Wyoming proxy (`scripts/voice_id/proxy.py`) runs as a sidecar
   in `wyoming-whisper` pod (`gitops/voice/whisper.yaml`) listening on port `10300`.
   The actual Whisper STT engine listens upstream on `127.0.0.1:10301`.
2. As the client streams audio, the proxy transparently forwards audio events to
   Whisper while buffering the 16kHz PCM audio in memory.
3. Upon `audio-stop`, the proxy uses `sherpa-onnx` CAMP++ ONNX model
   (`3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx`) to compute a 512-dimensional
   speaker embedding vector in ~35ms on CPU.
4. Audio samples shorter than 3.5 seconds are tiled to 3.5s to provide the
   receptive field required by the neural network for high-confidence classification.
5. The embedding is scored via cosine similarity against enrolled profiles
   in `gitops/voice/voice-id.yaml` (ConfigMap `wyoming-voice-id-config`).
6. If the top score exceeds `threshold` (0.35) and exceeds the runner-up by
   `min_margin` (0.10), the speaker identity is confirmed (`Rupan` or `Sam`).
7. When Whisper returns the `transcript` event, the proxy prefixes `speaker <Name>`
   (e.g. `speaker Sam play some Kanye`) before sending it back to Home Assistant.
8. `home-assistant/automations/jarvis_voice_music_playback.yaml` and
   `home-assistant/scripts/jarvis_play_media.yaml` read the speaker identity and route
   music requests directly to Sam's YouTube Music or Rupan's Spotify.

### Speaker enrollment procedure

To add or update speaker voice profiles:
1. Obtain ~20-30s of clear speech in any format (.wav, .m4a, .mp3). Prefer
   far-field samples recorded through the satellite mic itself
   (`pw-record --target=<quadcast-id> --rate=16000 --channels=1`) from the
   usual speaking spot: close-mic enrollment scores poorly against living-room
   audio. Re-enrolling one speaker must keep the others: pass the existing
   enrollment wavs (kept next to the model) for unchanged speakers, since the
   script rewrites the whole file. Keep threshold 0.35 / min_margin 0.10 as
   written by `scripts/voice_id/enroll.py` (a copy under the model volume has
   different defaults; the repo script is authoritative).
2. Convert to 16kHz mono WAV:
   ```sh
   ffmpeg -i user.m4a -ar 16000 -ac 1 /tmp/user.wav
   ```
3. Run the enrollment script inside the voice container or development shell:
   ```sh
   python3 scripts/voice_id/enroll.py \
     --model /persist/voice-models/whisper/voice-id/model.onnx \
     --speaker Rupan /tmp/rupan.wav \
     --speaker Sam /tmp/sam.wav \
     --output scripts/voice_id/profiles.json
   ```
4. Regenerate `gitops/voice/voice-id.yaml` ConfigMap:
   ```sh
   python3 -c "
   import yaml
   with open('scripts/voice_id/proxy.py') as f: proxy = f.read()
   with open('scripts/voice_id/profiles.json') as f: prof = f.read()
   manifest = {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'wyoming-voice-id-config', 'namespace': 'voice'}, 'data': {'proxy.py': proxy, 'profiles.json': prof}}
   def p(d, data): return d.represent_scalar('tag:yaml.org,2002:str', data, style='|' if len(data.splitlines()) > 1 else None)
   yaml.add_representer(str, p)
   with open('gitops/voice/voice-id.yaml', 'w') as f:
       f.write('# yamllint disable rule:line-length\n')
       yaml.dump(manifest, f, default_flow_style=False, sort_keys=False, width=120)
   "
   ```
5. Commit and let Flux apply the updated ConfigMap.


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
- Mic not detected or satellite in CrashLoopBackOff: verify Pipewire/WirePlumber
  sees the QuadCast on `homelab-05` via `wpctl status`. WirePlumber assigns it
  top priority 2500 (`~alsa_input.*QuadCast.*`), and the satellite container
  matches on substring `QuadCast` (first substring hit wins, so if several
  QuadCast nodes appear, confirm the USB source is listed first). For the exact
  Pulse source names the container sees, run it once with `LIST_DEVICES=1`.
- Soundbar loses sound after switching inputs: HDMI audio requires active video
  clocking. On `homelab-05`, `satellite-hdmi-audio-clock.service` runs as a
  continuous daemon re-clocking `HDMI-A-2` via `wlr-randr` whenever the soundbar
  reconnects. The soundbar PCM is onboard `pro-output-3`, pinned as default
  output at WirePlumber priority 3000 (measured 2026-09-18: the only onboard
  PCM reaching the soundbar); Nvidia HDMI stays at 2000, onboard fallback at
  1000, QuadCast headphone jack at 500. If the soundbar slept through silence,
  its kernel audio descriptor goes stale (`eld_valid 0` under
  `/proc/asound/PCH/eld*` while EDID is still present): toggle `HDMI-A-2` off
  and on via `wlr-randr` as the kiosk user to force a modeset and repopulate
  the ELD, then confirm with a test tone. Check
  `systemctl status satellite-hdmi-audio-clock` if soundbar audio does not return.
  The daemon pins HDMI-A-2 to 1920x1080, not just enabled: a soundbar/TV
  hotplug can bring that output back at 4K, and an overlapping 4K output
  crops the kiosk face on the 1080p primary down to one eye corner. 1080p
  still provides the video clock HDMI audio needs.
- PipeWire WebRTC echo cancellation evaluated 2026-09-18 and parked: the
  `libpipewire-module-echo-cancel` source exposed the mic with 0.0 dB measured
  reduction on both tonal and wideband playback (correct links, correct
  reference, 10 s stationary signal). Suspected USB-mic vs HDMI clock drift
  defeating the canceller. Do not retry without a new measurement showing
  cancellation. The deterministic mitigations are mic mute during TTS and a
  transcript sanity guard in the voice-id proxy (both pending as of 2026-09-18).
