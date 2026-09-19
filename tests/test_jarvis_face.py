from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FACE_DIR = REPO_ROOT / "home-assistant" / "www" / "jarvis"


def read_face(name: str) -> str:
    return (FACE_DIR / name).read_text(encoding="utf-8")


class JarvisFaceSelfUpdateTest(unittest.TestCase):
    def test_config_has_integer_face_version(self) -> None:
        config = json.loads(read_face("config.json"))
        self.assertIn("face_version", config)
        self.assertIsInstance(config["face_version"], int)
        self.assertGreater(config["face_version"], 0)

    def test_index_html_versions_assets_through_loader(self) -> None:
        html = read_face("index.html")
        self.assertIn('id="face-css"', html)
        self.assertIn("encodeURIComponent(v)", html)
        self.assertNotIn('<script src="app.js', html)

    def test_app_js_polls_face_version(self) -> None:
        js = read_face("app.js")
        self.assertIn("face_version", js)
        self.assertIn("setInterval", js)
        self.assertIn("__jarvisFaceVersionTarget", js)
        self.assertGreaterEqual(js.count("cache: 'no-store'"), 2)

    def test_music_state_wiring(self) -> None:
        config = json.loads(read_face("config.json"))
        self.assertIn("face_color_music", config)
        js = read_face("app.js")
        self.assertIn("music:", js)
        self.assertIn("state-music", js)
        self.assertIn("state === 'playing')", js)
        branch = js.split("state === 'playing')")[1].split("Default: Idle")[0]
        self.assertIn("setState('music'", branch)
        self.assertNotIn("setState('responding'", branch)
        html_css = read_face("style.css")
        self.assertIn("#app.state-music", html_css)

    def test_music_visualizer_replaces_face(self) -> None:
        js = read_face("app.js")
        self.assertIn("drawMusicVisualizer", js)
        self.assertIn("if (exprName === 'music')", js)
        self.assertNotIn("equalizer strip under the eyes", js)
        self.assertNotIn("nBars = 11", js)

    def test_music_label_shows_track(self) -> None:
        js = read_face("app.js")
        self.assertIn("media_title", js)
        self.assertIn("media_artist", js)
        self.assertIn("JARVIS // PLAYING // ", js)

    def test_kiosk_boot_url_matches_face_version(self) -> None:
        config = json.loads(read_face("config.json"))
        kiosk = (
            REPO_ROOT / "flake" / "hosts" / "homelab-05" / "default.nix"
        ).read_text(encoding="utf-8")
        match = re.search(r'url = "([^"]+/local/jarvis/index\.html\?v=([^"]+))"', kiosk)
        self.assertIsNotNone(match, "kiosk URL must carry the face ?v=")
        assert match is not None
        self.assertEqual(match.group(2), str(config["face_version"]))


if __name__ == "__main__":
    unittest.main()
