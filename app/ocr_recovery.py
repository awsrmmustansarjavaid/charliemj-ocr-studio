"""Targeted second-pass recovery for screenshots that OCR as plain text.

This is deliberately outside ``ui.py`` so the reliability layer can be tested
and evolved without changing the four-panel UI implementation. Balanced OCR
normally performs one full-image pass; when a dense image produces a plain-text
result with enough lines to plausibly be a grid/card, this layer retries the
same image at 3x scale and keeps the more structured result when it scores
better.
"""
from __future__ import annotations

from . import layout, ocr_engine
from .config import cfg


def _recover(self, original, img, min_pairs):
    best = original(self, img, min_pairs)
    if cfg["accuracy"] != "Balanced":
        return best
    if getattr(best, "kind", "") != "text" or len(getattr(best, "lines", ())) < 6:
        return best

    code, c1, c2 = self.codes()
    words, grid = ocr_engine.read_words(img, code, 3)
    reader = ocr_engine.make_cell_reader(grid, code, c1, c2)
    retry = layout.analyze(
        words,
        cfg["lang"],
        cfg["min_conf"],
        ocr_engine.make_refiner(grid, c1, c2),
        reader,
        min_pairs=min_pairs,
        size=grid.size,
        deep=True,
    )
    return retry if layout.score(retry) > layout.score(best) else best


def install(AppClass):
    """Patch App.smart with the targeted dense-screenshot recovery pass."""
    if getattr(AppClass, "_ocr_recovery_installed", False):
        return
    original = AppClass.smart

    def smart(self, img, min_pairs):
        return _recover(self, original, img, min_pairs)

    AppClass.smart = smart
    AppClass._ocr_recovery_installed = True
