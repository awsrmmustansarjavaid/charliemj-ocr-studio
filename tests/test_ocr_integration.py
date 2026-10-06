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


@unittest.skipUnless(HAS_TESS, "Tesseract is not installed")
class GloveCardTests(unittest.TestCase):
    """The flashcard that used to give only 10 vocabulary items: 12 labelled pictures + the title = 13 phrases."""

    @classmethod
    def setUpClass(cls):
        from PIL import Image
        from make_poster import make_card
        path = os.path.join(tempfile.mkdtemp(), "card.png")
        cls.truth = make_card(path, tight=0.9)                       # labels almost touch their neighbours
        cls.img = Image.open(path)

    def smart(self, deep=False):
        from app import layout, ocr_engine as oe
        words, g = oe.read_words(self.img, "tur+eng")
        return layout.analyze(words, "Turkish", 45, oe.make_refiner(g, "tur", "eng"),
                              oe.make_cell_reader(g, "tur+eng", "tur", "eng"), size=g.size, deep=deep)

    def test_all_twelve_cells_and_the_title_are_found(self):
        res = self.smart()
        want = {(a.lower(), b.lower()) for a, b in self.truth[1:]}
        got = {(a.lower(), b.lower()) for a, b in res.rows}
        self.assertEqual(want, got)                                   # nothing missing, nothing cut off, nothing invented
        self.assertEqual((res.title, res.subtitle), self.truth[0])
        self.assertEqual(res.grid, (3, 4))
        self.assertEqual(res.unread, 0)

    def test_editor_notes_list_thirteen_phrases(self):
        from app import layout
        res = self.smart()
        notes = layout.to_notes(res, layout.to_markdown(res, "Turkish", "English"))
        self.assertEqual(notes.count("\n- **"), 13)                   # 12 pictures + the title as a vocabulary item

    def test_raw_contains_every_word_of_the_card(self):
        from app import ocr_engine as oe
        raw = oe.read_raw(self.img, "tur+eng").lower()
        for a, b in self.truth[1:]:
            for word in (a + " " + b).split():
                self.assertIn(word.lower(), raw, word)


if __name__ == "__main__":
    unittest.main()
