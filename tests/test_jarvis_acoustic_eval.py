import unittest

from scripts.jarvis_acoustic_eval import normalize, word_error_rate


class AcousticScoringTest(unittest.TestCase):
    def test_normalize_ignores_case_and_punctuation(self) -> None:
        self.assertEqual(normalize("Turn on Govee!"), "turn on govee")

    def test_word_error_rate(self) -> None:
        self.assertEqual(word_error_rate("turn on lights", "turn on lights"), 0.0)
        self.assertAlmostEqual(word_error_rate("turn on lights", "turn lights"), 1 / 3)
