"""
Integration test: real Tesseract OCR on a generated poster that looks like the Instagram
vocabulary posts this app is built for (3 x 5 photo grid, watermark, phone UI, caption).

Skipped automatically when Tesseract (with Turkish data) is not installed.
    python -m unittest discover -s tests -v
"""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
HAS_TESS = shutil.which("tesseract") is not None or os.path.exists(os.path.join(os.path.dirname(__file__), "..", "tesseract"))


@unittest.skipUnless(HAS_TESS, "Tesseract is not installed")
class PosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PIL import Image
        from make_poster import PAIRS, make_poster
        path = os.path.join(tempfile.mkdtemp(), "poster.png")
        make_poster(path)
        cls.img, cls.pairs = Image.open(path), PAIRS

    def test_smart_finds_all_pairs_and_ignores_phone_ui(self):
        from app import layout, ocr_engine as oe
        words, g = oe.read_words(self.img, "tur+eng")
        res = layout.analyze(words, "Turkish", 45, oe.make_refiner(g, "tur", "eng"), oe.make_cell_reader(g, "tur+eng"))
        want = {(a.lower(), b.lower()) for a, b in self.pairs}
        got = {(a.lower(), b.lower()) for a, b in res.rows}
        self.assertEqual(res.kind, "bilingual")
        self.assertGreaterEqual(len(want & got), 11)          # at least 11 of 12 exactly right
        self.assertLessEqual(len(got - want), 1)               # (almost) nothing invented
        self.assertEqual(res.title, "")                        # "Posts" / usernames are not a title
        self.assertFalse(any("DESCRIBE" in a + b for a, b in res.rows))   # the caption is not a table row

    def test_raw_contains_every_word(self):
        from app import ocr_engine as oe
        raw = oe.read_raw(self.img, "tur+eng").lower()
        for a, b in self.pairs:
            for word in (a + " " + b).replace("'", " ").split():
                self.assertIn(word.lower(), raw, word)


if __name__ == "__main__":
    unittest.main()
