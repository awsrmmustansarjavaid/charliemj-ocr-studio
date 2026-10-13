import unittest

from app import languages
from app.config import LANGS


class LanguageTests(unittest.TestCase):
    def test_friendly_language_map_contains_non_turkish_languages(self):
        self.assertEqual(languages.FRIENDLY["deu"], "German")
        self.assertEqual(languages.FRIENDLY["jpn"], "Japanese")
        self.assertEqual(languages.FRIENDLY["ara"], "Arabic")

    def test_install_does_not_make_turkish_a_special_case(self):
        languages.install()
        self.assertIn("eng", LANGS)
        self.assertIn("tur", LANGS)
        self.assertEqual(LANGS["eng"], "eng")

    def test_invalid_pack_code_is_rejected_before_network(self):
        with self.assertRaises(ValueError):
            languages.install_pack("../bad")


if __name__ == "__main__":
    unittest.main()
