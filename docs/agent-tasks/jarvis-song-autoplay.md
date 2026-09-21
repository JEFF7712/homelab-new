# Agent Task: jarvis-song-autoplay

Status: `complete`

Base commit: `791a2e45da7b51b32d20e2ef64811a28a3f81e35`

Owner: `antigravity`

Exported at: `2026-09-21T23:30:00.000000+00:00`

## Objective

Enable automatic continuous playback (radio mode) in Music Assistant when Jarvis plays individual songs or tracks, so playback continues with related songs rather than stopping after one track.

## Acceptance criteria

- [x] When a user or voice intent requests a song or track, Music Assistant begins playback and continues autoplaying related tracks via radio mode (`extra: { radio_mode: true }` passed on `media_player.play_media`).
- [x] Full album and playlist playback retains standard queue behavior (`autoplay` defaults to false when `media_content_type` is not `music` or `track`), while allowing explicit overrides via the new `autoplay` boolean field in `script.jarvis_play_media`.
- [x] Canonical conversation prompt and runbook in `docs/runbooks/jarvis-voice.md` document song autoplay and radio mode routing.
- [x] Unit test `test_jarvis_play_media_autoplay` in `tests/test_jarvis_voice_eval.py` validates script field definitions, `use_radio_mode` boolean evaluation, and `extra: radio_mode` passing.
- [x] All offline validation gates (`scripts/checks/home-assistant.sh`, `tests/test_jarvis_voice_eval.py`, `fmt-check`, `ha-validate`, `yamllint`, `scripts/checks/python.sh`) pass cleanly.

## Owned source

- `home-assistant/scripts/jarvis_play_media.yaml`
- `docs/runbooks/jarvis-voice.md`
- `tests/test_jarvis_voice_eval.py`
- `docs/agent-tasks/jarvis-song-autoplay.md`

## Verification

- `nix develop ./flake --command python -m unittest tests/test_jarvis_voice_eval.py -v`: 23/23 tests pass.
- `nix develop ./flake --command bash scripts/checks/home-assistant.sh`: 79 unit tests pass, 88 resources pass schema/offline validation cleanly, yamllint 0 errors.
- `nix develop ./flake --command ./scripts/checks/python.sh`: 499 tests pass.
- `nix develop ./flake --command just fmt-check`: 106 files formatted cleanly across ruff, nixfmt, and tofu fmt.
- `nix develop ./flake --command python scripts/checks/docs.py`: clean.
- `nix develop ./flake --command python scripts/checks/whitespace.py`: clean.

## Uncommitted work

This handoff does not contain uncommitted file content. Recover it from the original checkout, or create and transfer a reviewed patch before moving to another machine.
