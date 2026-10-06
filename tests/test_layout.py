"""
Unit tests for app/layout.py.

They use synthetic word boxes (no OCR, no GUI), so they run anywhere:
    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))      # lets "from make_poster import ..." work however the tests are started

from app.layout import (Word, analyze, build_segments, drop_noise, extract_pairs,
                        target_score, to_markdown, to_plain)


def card_grid(pairs, cols=4, pitch=250, row_h=300):
    """Fake OCR output for a card grid: a label with its translation printed right below it."""
    words = []
    for i, (a, b) in enumerate(pairs):
        x, y = 40 + (i % cols) * pitch, 100 + (i // cols) * row_h
        for k, (text, dy) in enumerate(((a, 0), (b, 26))):
            cx = x
            for tok in text.split():
                w = 11 * len(tok)
                words.append(Word(tok, cx, y + dy, cx + w, y + dy + 20, 92))
                cx += w + 7
    return words


PAIRS = [("kışlık eldiven", "winter gloves"), ("muayene eldiveni", "medical gloves"),
         ("temizlik eldiveni", "cleaning gloves"), ("iş eldiveni", "work gloves"),
         ("deri eldiven", "leather gloves"), ("bahçe eldiveni", "gardening gloves")]


class LayoutTests(unittest.TestCase):
    def test_columns_are_split_into_separate_segments(self):
        segs = build_segments(card_grid(PAIRS))
        self.assertEqual(len(segs), 12)                     # 6 labels + 6 translations

    def test_card_grid_becomes_ordered_table(self):
        res = analyze(card_grid(PAIRS), "Turkish")
        self.assertEqual(res.kind, "bilingual")
        self.assertEqual(res.rows[0], ("kışlık eldiven", "winter gloves"))
        self.assertEqual(res.rows[4], ("deri eldiven", "leather gloves"))   # reading order: row by row
        self.assertEqual(len(res.rows), 6)

    def test_swapped_orientation_is_detected(self):
        flipped = [(b, a) for a, b in PAIRS]                 # English above Turkish
        res = analyze(card_grid(flipped), "Turkish")
        self.assertEqual(res.rows[1], ("muayene eldiveni", "medical gloves"))

    def test_two_column_table(self):
        words = []
        for i, (a, b) in enumerate([("Merhaba", "Hello"), ("Günaydın", "Good morning"), ("Nasılsın?", "How are you?")]):
            words += [Word(a, 80, 100 + i * 60, 250, 130 + i * 60, 95), Word(b, 600, 100 + i * 60, 760, 130 + i * 60, 95)]
        res = analyze(words, "Turkish")
        self.assertEqual(res.method, "horizontal")
        self.assertEqual(res.rows[1], ("Günaydın", "Good morning"))

    def test_urdu_script_decides_orientation(self):
        self.assertGreater(target_score("السلام علیکم", "Urdu"), 0)
        self.assertLess(target_score("Hello", "Urdu"), 0)

    def test_noise_is_dropped(self):
        words = [Word("O)", 0, 0, 20, 20, 90), Word("7:36", 30, 0, 80, 20, 90), Word("Merhaba", 0, 50, 90, 70, 90),
                 Word("blur", 0, 100, 60, 120, 20)]
        kept = [s.text for s in drop_noise(build_segments(words), 45)]
        self.assertEqual(kept, ["Merhaba"])

    def test_plain_text_falls_back_to_clean_lines(self):
        words = [Word("Bugün", 10, 10, 70, 30, 90), Word("hava", 80, 10, 130, 30, 90),
                 Word("çok", 10, 40, 50, 60, 90), Word("güzel", 60, 40, 120, 60, 90)]
        res = analyze(words, "Turkish")
        self.assertEqual(res.kind, "text")
        self.assertEqual(res.lines, ["Bugün hava", "çok güzel"])

    def test_markdown_roundtrip_and_swap(self):
        res = analyze(card_grid(PAIRS), "Turkish")
        md = to_markdown(res, "Turkish", "English")
        self.assertEqual(extract_pairs(md)[0], ("kışlık eldiven", "winter gloves"))
        swapped = extract_pairs(to_markdown(res, "Turkish", "English", swap=True))
        self.assertEqual(swapped[0], ("winter gloves", "kışlık eldiven"))

    def test_extract_pairs_reads_ai_bullets(self):
        self.assertEqual(extract_pairs("- **güzel** — beautiful"), [("güzel", "beautiful")])

    def test_empty_input(self):
        self.assertEqual(analyze([], "Turkish").kind, "empty")
        self.assertEqual(to_markdown(analyze([], "Turkish")), "(no text found)")

    def test_to_plain(self):
        md = "### Title\n\n|  # | A | B |\n|----|---|---|\n|  1 | x | y |\n- **w** — m"
        self.assertEqual(to_plain(md), "Title\n\nx — y\n• w — m")


class GridCompletionTests(unittest.TestCase):
    """A card grid in which a whole row and a whole column were not found by the first OCR pass."""

    def setUp(self):
        from make_poster import GLOVES
        self.pairs = GLOVES
        self.all = card_grid(GLOVES, pitch=300)                       # 4 columns x 3 rows

    def reader(self):
        """Fake read_cell(box): returns the two lines of the pair whose label lies in the box."""
        by_pair = {}
        for i, (a, b) in enumerate(self.pairs):
            ws = [w for w in self.all if w.y0 in (100 + (i // 4) * 300, 126 + (i // 4) * 300) and 40 + (i % 4) * 300 <= w.x0 < 40 + (i % 4) * 300 + 290]
            by_pair[i] = (min(w.x0 for w in ws) + max(w.x1 for w in ws)) / 2
        def read_cell(box, snap=True, role=None):
            for i, (a, b) in enumerate(self.pairs):
                cy = 100 + (i // 4) * 300 + 23
                if box[0] <= by_pair[i] <= box[2] and box[1] <= cy <= box[3]:
                    return [(a, 96.0), (b, 96.0)]
            return []
        return read_cell

    def test_missing_row_and_column_are_recovered(self):
        keep = [w for i, (a, b) in enumerate(self.pairs) if i // 4 != 0 and i % 4 != 0
                for w in self.all if w.y0 in (100 + (i // 4) * 300, 126 + (i // 4) * 300)
                and 40 + (i % 4) * 300 <= w.x0 < 40 + (i % 4) * 300 + 290]
        without = analyze(keep, "Turkish", read_cell=None)
        self.assertLess(len(without.rows), 12)                        # the first pass alone loses cells
        res = analyze(keep, "Turkish", read_cell=self.reader(), size=(1100, 1100))
        self.assertEqual(sorted(res.rows), sorted(self.pairs))        # ... the grid completion gets all 12 back
        self.assertEqual(res.grid, (3, 4))

    def test_picture_chrome_is_not_taken_for_a_missing_row(self):
        res = analyze(self.all, "Turkish", read_cell=lambda box, snap=True, role=None: [("Posts", 90.0)], size=(1100, 1100))
        self.assertEqual(len(res.rows), 12)


class NotesTests(unittest.TestCase):
    def test_title_pair_is_a_vocabulary_item_too(self):
        from app.layout import Result, to_notes
        res = Result(kind="bilingual", title="ELDİVEN ÇEŞİTLERİ", subtitle="Types of Gloves", rows=[("kışlık eldiven", "winter gloves")])
        md = "|  # | T | E |\n|----|---|---|\n|  1 | kışlık eldiven | winter gloves |"
        notes = to_notes(res, md)
        self.assertIn("- **ELDİVEN ÇEŞİTLERİ** — Types of Gloves", notes)
        self.assertNotIn("ELDİVEN ÇEŞİTLERİ** —", to_notes(res, md, title_vocab=False))

    def test_ai_can_never_make_ocr_words_vanish(self):
        from app.layout import merge_missing
        md, added = merge_missing("# T\n- **gamze** — dimple", [("gamze", "dimple"), ("ben", "mole")])
        self.assertEqual(added, 1)
        self.assertIn("- **ben** — mole", md)
        self.assertEqual(merge_missing("- **Gamze** — dimple", [("gamze", "dimple")])[1], 0)     # case / small fixes are not duplicates


if __name__ == "__main__":
    unittest.main()
