import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import ocr_recovery


class OCRRecoveryTests(unittest.TestCase):
    def test_balanced_text_result_gets_one_scale3_recovery_pass(self):
        original = SimpleNamespace(kind="text", lines=["x"] * 8)
        retry = SimpleNamespace(kind="bilingual", rows=[("a", "b")] * 8, lines=[])
        app = SimpleNamespace(codes=lambda: ("tur+eng", "tur", "eng"))
        image = object()

        grid = SimpleNamespace(size=(900, 1200))
        with patch.dict(ocr_recovery.cfg, {"accuracy": "Balanced", "lang": "Turkish", "min_conf": 45}), \
             patch.object(ocr_recovery.layout, "score", side_effect=lambda r: 10 if r is retry else 1), \
             patch.object(ocr_recovery.ocr_engine, "read_words", return_value=([], grid)) as read_words, \
             patch.object(ocr_recovery.ocr_engine, "make_cell_reader", return_value=object()), \
             patch.object(ocr_recovery.ocr_engine, "make_refiner", return_value=object()), \
             patch.object(ocr_recovery.layout, "analyze", return_value=retry):
            result = ocr_recovery._recover(app, lambda *_: original, image, 3)

        self.assertIs(result, retry)
        read_words.assert_called_once_with(image, "tur+eng", 3)

    def test_text_result_can_use_relaxed_gate_when_first_structural_pass_stays_text(self):
        original = SimpleNamespace(kind="text", lines=["x"] * 8)
        first_retry = SimpleNamespace(kind="text", rows=[], lines=["x"] * 8)
        relaxed = SimpleNamespace(kind="bilingual", rows=[("a", "b")] * 12, lines=[])
        app = SimpleNamespace(codes=lambda: ("tur+eng", "tur", "eng"))
        image = object()
        grid = SimpleNamespace(size=(1080, 1920))

        with patch.dict(ocr_recovery.cfg, {"accuracy": "Balanced", "lang": "Turkish", "min_conf": 45}), \
             patch.object(ocr_recovery.layout, "score", side_effect=lambda r: 20 if r is relaxed else 1), \
             patch.object(ocr_recovery.ocr_engine, "read_words", return_value=([], grid)), \
             patch.object(ocr_recovery.ocr_engine, "make_cell_reader", return_value=object()), \
             patch.object(ocr_recovery.ocr_engine, "make_refiner", return_value=object()), \
             patch.object(ocr_recovery.layout, "analyze", side_effect=[first_retry, relaxed]) as analyze:
            result = ocr_recovery._recover(app, lambda *_: original, image, 3)

        self.assertIs(result, relaxed)
        self.assertEqual(analyze.call_args_list[0].kwargs["min_pairs"], 3)
        self.assertEqual(analyze.call_args_list[1].kwargs["min_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
