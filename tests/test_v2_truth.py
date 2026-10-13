"""Regression tests for the v2 immutable OCR coverage guard."""
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(__file__))

from app.layout import Word, merge_missing
from app.v2_truth import reconcile_result


class OCRTruthRegressionTests(unittest.TestCase):
    """The historical 13-vocabulary -> 11-result regression must never return."""

    @staticmethod
    def _words(count=13):
        words = []
        for i in range(count):
            y = 100 + i * 100
            words.append(Word(f"word{i + 1}", 40, y, 140, y + 20, 95))
            words.append(Word(f"meaning{i + 1}", 40, y + 25, 180, y + 45, 95))
        return words

    def test_thirteen_detected_items_recover_two_missing_pairs(self):
        """A layout result containing only 11 of 13 pairs is reconciled to 13."""
        all_pairs = [(f"word{i}", f"meaning{i}") for i in range(1, 14)]
        result = SimpleNamespace(
            kind="bilingual", rows=list(all_pairs[:11]), title="", subtitle=""
        )
        result = reconcile_result(result, self._words())

        self.assertEqual(len(result.rows), 13)
        self.assertIn(("word12", "meaning12"), result.rows)
        self.assertIn(("word13", "meaning13"), result.rows)
        self.assertEqual(result.coverage.recovered_pairs, 2)
        self.assertEqual(result.coverage.unrepresented, 0)
        self.assertTrue(result.coverage.complete)
        self.assertEqual(len(result.ocr_truth), 26)  # 13 source + 13 translation OCR observations

    def test_ai_output_cannot_drop_any_of_thirteen_sources(self):
        """AI Smart receives 11 rows but the deterministic OCR merge restores all 13."""
        rows = [(f"word{i}", f"meaning{i}") for i in range(1, 14)]
        ai = "\n".join(f"- **{a}** — {b}" for a, b in rows[:11])
        merged, added = merge_missing(ai, rows)

        self.assertEqual(added, 2)
        for a, b in rows:
            self.assertIn(f"**{a}** — {b}", merged)


if __name__ == "__main__":
    unittest.main()
