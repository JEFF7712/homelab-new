from __future__ import annotations

import json
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
MUSIC_STOP_AUTOMATION = (
    REPO_ROOT / "home-assistant" / "automations" / "jarvis_music_stop.yaml"
)
PLAY_MEDIA_SCRIPT = REPO_ROOT / "home-assistant" / "scripts" / "jarvis_play_media.yaml"
MUSIC_STOP_INTENT = "MusicStop"
SATELLITE_MEDIA_PLAYER = "media_player.homelab_05_satellite_media_player"
VOICE_EXTRA_TARGETS = frozenset({SATELLITE_MEDIA_PLAYER})
MUSIC_INTENTS = {
    "MusicArtist": "artist",
    "MusicPlaylist": "playlist",
    "MusicYoutubeArtist": "youtube_artist",
    "MusicYoutubeTrack": "youtube_track",
}
HOME_FILE = (
    REPO_ROOT / "home-assistant" / "custom_sentences" / "en" / "jarvis_home.yaml"
)
NUDGE_FILE = (
    REPO_ROOT / "home-assistant" / "custom_sentences" / "en" / "jarvis_nudge.yaml"
)
DONE_SCRIPTS = {"JarvisBrightnessNudge", "JarvisMovieMode"}
ALIAS_INTENTS = {"JarvisAliasOn": "light.turn_on", "JarvisAliasOff": "light.turn_off"}
ALIAS_FILE = (
    REPO_ROOT / "home-assistant" / "custom_sentences" / "en" / "jarvis_alias.yaml"
)
TEMPLATE_QUERIES = {
    "JarvisWhatsPlaying": "media_player.homelab_05_satellite_media_player_2",
    "JarvisTempDownstairs": "sensor.living_room_ac_ambient_temperature_degf",
    "JarvisKitchenLightsState": "light.kitchen_lights",
    "JarvisAcState": "sensor.living_room_ac_mode",
}
BUILTIN_DYNAMIC = {"HassShoppingListAddItem"}
NEON_PINK_RGB = [255, 16, 240]
MIN_CASES = 30
MAX_CASES = 50


def _parse_template(template: str) -> list:
    parts: list = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        for word in buf.split():
            parts.append(("lit", word.lower()))
        buf = ""

    i = 0
    while i < len(template):
        ch = template[i]
        if ch in "[{(":
            closer = {"[": "]", "{": "}", "(": ")"}[ch]
            j = template.index(closer, i)
            flush()
            inner = template[i + 1 : j]
            if ch == "{":
                parts.append(("slot",))
            elif ch == "(":
                parts.append(
                    (
                        "alt",
                        [[w.lower() for w in c.split()] for c in inner.split("|")],
                    )
                )
            elif "|" in inner:
                parts.append(
                    (
                        "optalt",
                        [[w.lower() for w in c.split()] for c in inner.split("|")],
                    )
                )
            else:
                parts.append(("opt", [w.lower() for w in inner.split()]))
            i = j + 1
        else:
            buf += ch
            i += 1
    flush()
    return parts


def _consume(part: tuple, words: list, pos: int) -> set:
    kind = part[0]
    if kind == "lit":
        if pos < len(words) and words[pos] == part[1]:
            return {pos + 1}
        return set()
    if kind == "slot":
        return set(range(pos + 1, len(words) + 1))
    if kind in ("alt", "optalt"):
        out = {pos} if kind == "optalt" else set()
        for choice in part[1]:
            current = pos
            for word in choice:
                if current < len(words) and words[current] == word:
                    current += 1
                else:
                    break
            else:
                out.add(current)
        return out
    if kind == "opt":
        current = pos
        for word in part[1]:
            if current < len(words) and words[current] == word:
                current += 1
            else:
                return {pos}
        return {pos, current}
    raise AssertionError(f"unknown part {kind}")


def sentence_matches(template: str, say: str) -> bool:
    """Match an utterance against a hassil-style sentence template."""
    words = [w.strip(".,?!") for w in say.lower().split()]
    positions = {0}
    for part in _parse_template(template):
        following = set()
        for pos in positions:
            following.update(_consume(part, words, pos))
        positions = following
        if not positions:
            return False
    return len(words) in positions


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
    scenes_dir = REPO_ROOT / "home-assistant" / "scenes"
    if scenes_dir.is_dir():
        for f in scenes_dir.glob("*.yaml"):
            try:
                name = yaml.safe_load(f.read_text(encoding="utf-8")).get("name", f.stem)
            except yaml.YAMLError:
                name = f.stem
            slug = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
            known.add(f"scene.{slug}")
    return known


class EvalCorpusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = yaml.safe_load(CORPUS_FILE.read_text(encoding="utf-8"))
        cls.terse = yaml.safe_load(TERSE_FILE.read_text(encoding="utf-8"))
        cls.colors = yaml.safe_load(COLORS_FILE.read_text(encoding="utf-8"))
        cls.home = yaml.safe_load(HOME_FILE.read_text(encoding="utf-8"))
        cls.nudge = yaml.safe_load(NUDGE_FILE.read_text(encoding="utf-8"))
        cls.alias = yaml.safe_load(ALIAS_FILE.read_text(encoding="utf-8"))
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
                    LOCAL_INTENTS
                    | {SIGNATURE_INTENT}
                    | set(MUSIC_INTENTS)
                    | {MUSIC_STOP_INTENT}
                    | DONE_SCRIPTS
                    | set(TEMPLATE_QUERIES)
                    | BUILTIN_DYNAMIC
                    | set(ALIAS_INTENTS),
                    case["id"],
                )
                if case.get("dynamic"):
                    self.assertEqual(case["targets"], [], case["id"])
                else:
                    self.assertTrue(case["targets"], case["id"])
                self.assertTrue(case["response"].strip(), case["id"])
            else:
                self.assertTrue(case["tool"], case["id"])
                self.assertTrue(case.get("notes", "").strip(), case["id"])

    def test_local_responses_are_terse(self) -> None:
        for case in self.cases:
            if case["path"] != "local" or case.get("dynamic"):
                continue
            self.assertLessEqual(len(case["response"].split()), 3, case["id"])

    def test_local_intents_have_terse_override(self) -> None:
        overrides = self.terse.get("responses", {}).get("intents", {})
        for case in self.cases:
            if case["path"] != "local" or case["intent"] not in LOCAL_INTENTS:
                continue
            self.assertIn(case["intent"], overrides, case["id"])
            self.assertEqual(
                overrides[case["intent"]].get("default"), "Done.", case["id"]
            )
            self.assertEqual(case["response"], "Done.", case["id"])

    def test_light_set_slot_responses_are_terse(self) -> None:
        light_set = self.terse["responses"]["intents"]["HassLightSet"]
        for slot in ("brightness", "color", "temperature"):
            self.assertEqual(light_set.get(slot), "Done.", slot)

    def test_builtin_sentence_extensions(self) -> None:
        intents = self.core["conversation"]["intents"]
        sentences = intents["HassLightSet"]
        self.assertTrue(any("dim" in s for s in sentences), "dim phrasing present")
        self.assertTrue(
            any("brighten" in s for s in sentences), "brighten phrasing present"
        )
        for sentence in sentences:
            self.assertIn("{name}", sentence)
            self.assertIn("{brightness}", sentence)

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
        allowed = self.known | VOICE_EXTRA_TARGETS
        for case in self.cases:
            if case["path"] != "local":
                continue
            for entity_id in case["targets"]:
                self.assertIn(entity_id, allowed, f"{case['id']}: {entity_id}")

    def test_music_stop_cases_match_trigger_sentences(self) -> None:
        automation = yaml.safe_load(MUSIC_STOP_AUTOMATION.read_text(encoding="utf-8"))
        by_id = {
            t.get("id"): t.get("command", []) for t in automation.get("triggers", [])
        }
        self.assertTrue(by_id.get("stop"), "stop trigger present")
        actions = automation.get("actions", [])
        pause_call = next(
            a for a in actions if a.get("action") == "media_player.media_pause"
        )
        self.assertEqual(pause_call["target"]["entity_id"], SATELLITE_MEDIA_PLAYER)
        response = next(
            a["set_conversation_response"]
            for a in actions
            if "set_conversation_response" in a
        )
        self.assertIn("Paused.", response)
        for case in self.cases:
            if case.get("intent") != MUSIC_STOP_INTENT:
                continue
            say = case["say"].strip().rstrip(".?!")
            matched = any(sentence_matches(template, say) for template in by_id["stop"])
            self.assertTrue(matched, f"{case['id']}: {say!r} matches no stop sentence")
            self.assertEqual(case["response"], "Paused.", case["id"])
            self.assertEqual(case["targets"], [SATELLITE_MEDIA_PLAYER], case["id"])

    def test_done_scripts(self) -> None:
        scripts = self.core["intent_script"]
        nudge = scripts["JarvisBrightnessNudge"]
        self.assertEqual(nudge["speech"]["text"], "Done.")
        flat = json.dumps(nudge["action"])
        self.assertIn("light.downstairs_lights", flat)
        self.assertIn("brightness_step_pct", flat)
        movie = scripts["JarvisMovieMode"]
        self.assertEqual(movie["speech"]["text"], "Done.")
        self.assertEqual(
            movie["action"][0]["target"]["entity_id"], "scene.movie_low_living_room"
        )
        directions = {
            v["in"]: v["out"] for v in self.nudge["lists"]["jarvis_direction"]["values"]
        }
        self.assertEqual(directions, {"darker": "decrease", "brighter": "increase"})

    def test_template_queries(self) -> None:
        scripts = self.core["intent_script"]
        for intent, entity_id in TEMPLATE_QUERIES.items():
            speech = scripts[intent]["speech"]["text"]
            self.assertTrue("{{" in speech or "{%" in speech, intent)
            self.assertIn(entity_id, speech, intent)
        for case in self.cases:
            if case.get("intent") not in TEMPLATE_QUERIES:
                continue
            self.assertTrue(case.get("dynamic"), case["id"])

    def test_builtin_dynamic(self) -> None:
        cases = [c for c in self.cases if c.get("intent") in BUILTIN_DYNAMIC]
        self.assertTrue(cases)
        for case in cases:
            self.assertTrue(case.get("dynamic"), case["id"])

    def test_alias_routing(self) -> None:
        self.assertEqual(self.alias.get("language"), "en")
        outs = {v["out"] for v in self.alias["lists"]["jarvis_alias"]["values"]}
        self.assertEqual(outs, {"light.bedroom_roku_lights", "light.all_govee_lights"})
        for entity_id in outs:
            self.assertIn(entity_id, self.known, entity_id)
        scripts = self.core["intent_script"]
        for intent, service in ALIAS_INTENTS.items():
            entry = scripts[intent]
            self.assertEqual(entry["speech"]["text"], "Done.")
            self.assertEqual(entry["action"][0]["service"], service)

    def test_home_sentences_match_cases(self) -> None:
        sentences: dict[str, list[str]] = {}
        for source in (self.home, self.nudge, self.alias):
            self.assertEqual(source.get("language"), "en")
            for intent, body in source.get("intents", {}).items():
                for block in body.get("data", []):
                    sentences.setdefault(intent, []).extend(block["sentences"])
        for case in self.cases:
            if case.get("intent") not in DONE_SCRIPTS | set(TEMPLATE_QUERIES) | set(
                ALIAS_INTENTS
            ):
                continue
            say = case["say"].strip().rstrip(".?!")
            matched = any(
                sentence_matches(template, say)
                for template in sentences[case["intent"]]
            )
            self.assertTrue(matched, f"{case['id']}: {say!r} matches no sentence")

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
        self.assertIn("Done.", response)
        self.assertIn("playback", response)
        script_call = next(
            a for a in actions if a.get("action") == "script.jarvis_play_media"
        )
        self.assertEqual(script_call.get("response_variable"), "playback")
        self.assertTrue(script_call.get("continue_on_error"))
        self.assertIn("trigger.id", script_call["data"]["media_content_type"])
        self.assertIn("youtube_music", script_call["data"]["platform"])
        for trigger_id in MUSIC_INTENTS.values():
            self.assertTrue(by_id.get(trigger_id), trigger_id)
            self.assertIn(trigger_id, script_call["data"]["media_content_type"])
        for case in self.cases:
            if case.get("intent") not in MUSIC_INTENTS:
                continue
            trigger_id = MUSIC_INTENTS[case["intent"]]
            say = case["say"].strip().rstrip(".?!")
            matched = any(
                sentence_matches(template, say) for template in by_id[trigger_id]
            )
            self.assertTrue(
                matched, f"{case['id']}: {say!r} matches no {trigger_id} sentence"
            )
            self.assertEqual(case["response"], "Done.", case["id"])
            self.assertEqual(case["targets"], ["script.jarvis_play_media"], case["id"])

    def test_artist_branch_plays_endless_mix(self) -> None:
        script = yaml.safe_load(PLAY_MEDIA_SCRIPT.read_text(encoding="utf-8"))
        choose = next(step["choose"] for step in script["sequence"] if "choose" in step)
        artist_branch = next(
            branch
            for branch in choose
            if "artist" in json.dumps(branch.get("conditions", []))
        )
        play_calls = [
            action
            for action in artist_branch["sequence"]
            if action.get("action") == "music_assistant.play_media"
        ]
        self.assertTrue(play_calls, "artist branch uses music_assistant.play_media")
        for call in play_calls:
            self.assertEqual(call["data"]["media_type"], "artist")
            self.assertTrue(call["data"]["radio_mode"])
            self.assertEqual(call["data"]["enqueue"], "replace")
            self.assertIn("artist_uri", call["data"]["media_id"])
        self.assertNotIn("media_player.play_media", json.dumps(artist_branch))


if __name__ == "__main__":
    unittest.main()
