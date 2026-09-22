import unittest

from scripts.voice_stt_switch import ADDRESSES, BACKENDS, preference_value


class PreferenceTest(unittest.TestCase):
    def test_preference_value_promotes_requested_backend(self) -> None:
        for backend in BACKENDS:
            parts = preference_value(backend).split(",")
            self.assertEqual(parts[0], f"{backend}={ADDRESSES[backend]}")
            self.assertEqual({part.split("=", 1)[0] for part in parts}, set(BACKENDS))
