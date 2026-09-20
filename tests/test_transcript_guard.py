"""Unit tests for the voice-id proxy transcript sanity guard.

Covers is_garbage_transcript from scripts.voice_id.proxy. These tests use
only the standard library so they run on the host; the classifier tests in
test_voice_id.py need numpy/sherpa and run in the container.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import yaml

from scripts.voice_id.proxy import is_garbage_transcript


class TestTranscriptGuard(unittest.TestCase):
    def test_empty_and_whitespace_dropped(self) -> None:
        self.assertTrue(is_garbage_transcript(""))
        self.assertTrue(is_garbage_transcript("   "))

    def test_repeated_token_dropped(self) -> None:
        self.assertTrue(is_garbage_transcript("Govee, Govee, Govee, Govee,"))
        self.assertTrue(is_garbage_transcript("Govee,"))
        self.assertTrue(is_garbage_transcript("no no no no"))

    def test_known_hallucinations_dropped(self) -> None:
        for text in (
            "Stu.",
            "Control.",
            "Further.",
            "Chew away.",
            "Say something.",
            "Today, whoever.",
            "You wait. Hey Jarvis, who am I?",
            "Govee, V",
        ):
            with self.subTest(text=text):
                self.assertTrue(is_garbage_transcript(text))

    def test_real_commands_kept(self) -> None:
        for text in (
            "Stop.",
            "Hey Jarvis, stop.",
            "Hey Jarvis.",
            "Turn off the downstairs lights.",
            "Lower your volume by 10%.",
            "What's my name?",
            "Done.",
            "Play some Kanye.",
        ):
            with self.subTest(text=text):
                self.assertFalse(is_garbage_transcript(text))

    def test_two_repeats_kept(self) -> None:
        self.assertFalse(is_garbage_transcript("okay okay"))


class TestVoiceIdConfigMapGenerator(unittest.TestCase):
    def test_generator_covers_deploy_sources(self) -> None:
        root = Path(__file__).resolve().parent.parent
        kust = yaml.safe_load(
            (root / "gitops" / "voice" / "kustomization.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("voice-id.yaml", kust.get("resources", []))
        gen = next(
            entry
            for entry in kust.get("configMapGenerator", [])
            if entry.get("name") == "wyoming-voice-id-config"
        )
        self.assertEqual(
            sorted(Path(f).name for f in gen["files"]),
            ["profiles.json", "proxy.py"],
        )
        for f in gen["files"]:
            self.assertTrue((root / "gitops" / "voice" / f).is_file(), f)

    def test_scripts_symlink_tracks_deploy_source(self) -> None:
        root = Path(__file__).resolve().parent.parent
        for name in ("proxy.py", "profiles.json"):
            link = root / "scripts" / "voice_id" / name
            self.assertTrue(link.is_symlink(), name)
            self.assertEqual(
                link.resolve(),
                (root / "gitops" / "voice" / "voice-id" / name).resolve(),
                name,
            )


if __name__ == "__main__":
    unittest.main()
