import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import ocr_recovery


class OCRRecoveryTests(unittest.TestCase):
    def test_balanced_text_result_gets_one_scale3_recovery_pass(self):
        original = SimpleNamespace(kind="text", lines=["x"] * 8)
        retry = SimpleNamespace(kind="bilingual", lines=["x"] * 8)
        app = SimpleNamespace(codes=lambda: ("tur+eng", "tur", "eng"))
        image = object()

        grid = SimpleNamespace(size=(900, 1200))
        with patch.object(ocr_recovery.layout, "score", side_effect=lambda r: 10 if r is retry else 1), \
             patch.object(ocr_recovery.ocr_engine, "read_words", return_value=([], grid)) as read_words, \
             patch.object(ocr_recovery.ocr_engine, "make_cell_reader", return_value=object()), \
             patch.object(ocr_recovery.ocr_engine, "make_refiner", return_value=object()), \
             patch.object(ocr_recovery.layout, "analyze", return_value=retry):
            with patch.object(ocr_recovery.cfg, "__getitem__", side_effect=lambda key: "Balanced" if key == "accuracy" else (45 if key == "min_conf" else "Turkish" if key == "lang" else None)):
                result = ocr_recovery._recover(app, lambda *_: original, image, 3)

        self.assertIs(result, retry)
        read_words.assert_called_once_with(image, "tur+eng", 3)


if __name__ == "__main__":
    unittest.main()
