"""Targeted recovery for screenshots that initially look like plain text.

Smart OCR is intentionally a full-image pass first.  Some dense bilingual
screenshots have enough OCR words to be useful but not enough clean geometric
pairs on the first pass, so they can be classified as plain text.  This module
adds a bounded structural retry without changing the four-panel UI.
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
    # One bounded 3x pass is enough to recover small text without making every
    # ordinary screenshot pay the cost of a second OCR run.
    words, grid = ocr_engine.read_words(img, code, 3)
    reader = ocr_engine.make_cell_reader(grid, code, c1, c2)
    refiner = ocr_engine.make_refiner(grid, c1, c2)

    retry = layout.analyze(
        words,
        cfg["lang"],
        cfg["min_conf"],
        refiner,
        reader,
        min_pairs=min_pairs,
        size=grid.size,
        deep=True,
    )

    # A dense screenshot can have several real bilingual cards while the first
    # pass misses just enough pair geometry to fail the normal min_pairs gate.
    # Relax only that classification gate for the recovery pass; never accept
    # fewer than three recovered rows for a whole-image Smart result.
    relaxed = retry
    if getattr(retry, "kind", "") != "bilingual":
        relaxed = layout.analyze(
            words,
            cfg["lang"],
            cfg["min_conf"],
            refiner,
            reader,
            min_pairs=1,
            size=grid.size,
            deep=True,
        )

    candidates = [best]
    if getattr(retry, "kind", "") == "bilingual":
        candidates.append(retry)
    if getattr(relaxed, "kind", "") == "bilingual" and len(getattr(relaxed, "rows", ())) >= max(3, min_pairs):
        candidates.append(relaxed)

    # Prefer a genuine structured result once it contains a real table-sized
    # set of rows.  Otherwise retain the original full-text result rather than
    # risking a false table classification.
    structured = [r for r in candidates if getattr(r, "kind", "") == "bilingual" and len(getattr(r, "rows", ())) >= max(3, min_pairs)]
    if structured:
        return max(structured, key=layout.score)
    return best


def install(AppClass):
    """Patch App.smart with the targeted dense-screenshot recovery pass."""
    if getattr(AppClass, "_ocr_recovery_installed", False):
        return
    original = AppClass.smart

    def smart(self, img, min_pairs):
        return _recover(self, original, img, min_pairs)

    AppClass.smart = smart
    AppClass._ocr_recovery_installed = True
