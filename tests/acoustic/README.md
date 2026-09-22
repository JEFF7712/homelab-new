# Jarvis acoustic regression corpus

Record 10 to 20 uncompressed, 16 kHz, mono PCM WAV clips through the production
QuadCast path. Recordings are private operator evidence and stay ignored under
`tests/acoustic/recordings/`; `manifest.json` is the reviewed label set.

The corpus must cover clean and noisy commands, distant speech, device and artist
names, room targets, music requests, and captured Jarvis TTS for echo rejection.
Use at least two speakers and retain natural pauses. Do not synthesize substitutes.

Run the same immutable corpus against every backend through a temporary port
forward to its backend Service. The runner emits per-case transcripts and word
error rates as JSON. A backend change is accepted only when it introduces no
unsafe target or action substitutions and meets the configured WER budget.
