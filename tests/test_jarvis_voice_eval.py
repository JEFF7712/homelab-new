from __future__ import annotations

import re
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_FILE = Path(__file__).resolve().parent / "jarvis_voice_eval_corpus.yaml"
TERSE_FILE = (
    REPO_ROOT / "home-assistant" / "custom_sentences" / "en" / "jarvis_terse.yaml"
)
CORE_FILE = REPO_ROOT / "home-assistant" / "core" / "configuration.yaml"
COLORS_FILE = (
    REPO_ROOT / "home-assistant" / "custom_sentences" / "en" / "jarvis_colors.yaml"
)

LOCAL_INTENTS = {"HassTurnOn", "HassTurnOff", "HassToggle", "HassLightSet"}
SIGNATURE_INTENT = "JarvisSignatureColor"
MUSIC_AUTOMATION = (
    REPO_ROOT / "home-assistant" / "automations" / "jarvis_voice_music_playback.yaml"
)
MUSIC_INTENTS = {"MusicArtist": "artist", "MusicPlaylist": "playlist"}
NEON_PINK_RGB = [255, 16, 240]
MIN_CASES = 30
MAX_CASES = 50


def sentence_matches(template: str, say: str) -> bool:
    """Match an utterance against a hassil-style sentence template."""
    pattern = re.escape(template)
    pattern = pattern.replace(r"\{query\}", ".+?")
    pattern = re.sub(r"\\\[([^\\]+?)\\\]\\ ", r"(?:\1 )?", pattern)
    pattern = re.sub(r"\\\[([^\\]+?)\\\]", r"(?:\1)?", pattern)
    pattern = pattern.replace(r"\(", "(?:").replace(r"\)", ")")
    pattern = pattern.replace(r"\|", "|")
    return re.fullmatch(pattern, say, re.IGNORECASE) is not None


def ha_loader() -> type[yaml.SafeLoader]:
    loader = type("HALoader", (yaml.SafeLoader,), {})
    loader.add_multi_constructor("!", lambda ldr, suffix, node: None)
    return loader


def known_entity_ids() -> set[str]:
    core = yaml.load(CORE_FILE.read_text(encoding="utf-8"), Loader=ha_loader())
    known: set[str] = set()
    for group in core.get("light", []):
        entities = group.get("entities", [])
        entity_id = group.get("entity_id")
        if isinstance(entity_id, str):
            known.add(entity_id)
        if isinstance(entities, list):
            known.update(e for e in entities if isinstance(e, str))
        name = group.get("name")
        if isinstance(name, str):
            slug = name.lower().replace(" ", "_")
            known.add(f"light.{slug}")
            known.add(f"switch.{slug}")
    for bridge in core.get("homekit", []):
        filt = bridge.get("filter", {}).get("include_entities", [])
        known.update(e for e in filt if isinstance(e, str))
    scripts_dir = REPO_ROOT / "home-assistant" / "scripts"
    if scripts_dir.is_dir():
        known.update(f"script.{f.stem}" for f in scripts_dir.glob("*.yaml"))
    return known


class EvalCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = yaml.safe_load(CORPUS_FILE.read_text(encoding="utf-8"))
        cls.terse = yaml.safe_load(TERSE_FILE.read_text(encoding="utf-8"))
        cls.colors = yaml.safe_load(COLORS_FILE.read_text(encoding="utf-8"))
        cls.core = yaml.load(CORE_FILE.read_text(encoding="utf-8"), Loader=ha_loader())
        cls.known = known_entity_ids()

    def test_corpus_size(self) -> None:
        self.assertGreaterEqual(len(self.cases), MIN_CASES)
        self.assertLessEqual(len(self.cases), MAX_CASES)

    def test_ids_unique(self) -> None:
        ids = [c["id"] for c in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_schema(self) -> None:
        for case in self.cases:
            self.assertIn(case["path"], ("local", "llm"), case["id"])
            self.assertTrue(case["say"].strip().rstrip(".").strip(), case["id"])
            if case["path"] == "local":
                self.assertIn(
                    case["intent"],
                    LOCAL_INTENTS | {SIGNATURE_INTENT} | set(MUSIC_INTENTS),
                    case["id"],
                )
                self.assertTrue(case["targets"], case["id"])
                self.assertTrue(case["response"].strip(), case["id"])
            else:
                self.assertTrue(case["tool"], case["id"])
                self.assertTrue(case.get("notes", "").strip(), case["id"])

    def test_local_responses_are_terse(self) -> None:
        for case in self.cases:
            if case["path"] != "local":
                continue
            self.assertLessEqual(len(case["response"].split()), 3, case["id"])

    def test_local_intents_have_terse_override(self) -> None:
        overrides = self.terse.get("responses", {}).get("intents", {})
        for case in self.cases:
            if (
                case["path"] != "local"
                or case["intent"] == SIGNATURE_INTENT
                or case["intent"] in MUSIC_INTENTS
            ):
                continue
            self.assertIn(case["intent"], overrides, case["id"])
            self.assertEqual(
                overrides[case["intent"]].get("default"), "Done.", case["id"]
            )
            self.assertEqual(case["response"], "Done.", case["id"])

    def test_signature_color_palette(self) -> None:
        self.assertEqual(self.colors.get("language"), "en")
        light_lists = {v["out"] for v in self.colors["lists"]["jarvis_light"]["values"]}
        color_lists = {v["out"] for v in self.colors["lists"]["jarvis_color"]["values"]}
        self.assertIn("neon_pink", color_lists)
        for entity_id in light_lists:
            self.assertIn(entity_id, self.known, entity_id)
        script = self.core["intent_script"][SIGNATURE_INTENT]
        self.assertEqual(script["speech"]["text"], "Done.")
        actions = script["action"]
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["service"], "light.turn_on")
        self.assertEqual(actions[0]["data"]["rgb_color"], NEON_PINK_RGB)

    def test_signature_color_cases_match_palette(self) -> None:
        light_lists = {v["out"] for v in self.colors["lists"]["jarvis_light"]["values"]}
        for case in self.cases:
            if case.get("intent") != SIGNATURE_INTENT:
                continue
            self.assertEqual(case["response"], "Done.", case["id"])
            for entity_id in case["targets"]:
                self.assertIn(entity_id, light_lists, f"{case['id']}: {entity_id}")

    def test_local_targets_exist_in_source(self) -> None:
        for case in self.cases:
            if case["path"] != "local":
                continue
            for entity_id in case["targets"]:
                self.assertIn(entity_id, self.known, f"{case['id']}: {entity_id}")

    def test_language_is_english(self) -> None:
        self.assertEqual(self.terse.get("language"), "en")

    def test_music_cases_match_trigger_sentences(self) -> None:
        automation = yaml.safe_load(MUSIC_AUTOMATION.read_text(encoding="utf-8"))
        by_id = {
            t.get("id"): t.get("command", []) for t in automation.get("triggers", [])
        }
        actions = automation.get("actions", [])
        response = next(
            a["set_conversation_response"]
            for a in actions
            if "set_conversation_response" in a
        )
        self.assertEqual(response, "Done.")
        script_call = next(
            a for a in actions if a.get("action") == "script.jarvis_play_media"
        )
        self.assertIn("trigger.id", script_call["data"]["media_content_type"])
        for trigger_id in MUSIC_INTENTS.values():
            self.assertTrue(by_id.get(trigger_id), trigger_id)
        for case in self.cases:
            if case.get("intent") not in MUSIC_INTENTS:
                continue
            trigger_id = MUSIC_INTENTS[case["intent"]]
            say = case["say"].strip().rstrip(".")
            matched = any(
                sentence_matches(template, say) for template in by_id[trigger_id]
            )
            self.assertTrue(
                matched, f"{case['id']}: {say!r} matches no {trigger_id} sentence"
            )
            self.assertEqual(case["response"], "Done.", case["id"])
            self.assertEqual(case["targets"], ["script.jarvis_play_media"], case["id"])


if __name__ == "__main__":
    unittest.main()
