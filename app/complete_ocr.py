"""Lossless OCR coverage for full screenshots.

The number of vocabulary pairs visible in one reference screenshot is NOT a
limit.  Smart OCR may structure the text, but the complete OCR text remains the
source of truth.  This module adds a small compatibility layer to the existing
App so older UI code cannot silently discard OCR lines.
"""
from __future__ import annotations

import re

from . import layout, ocr_engine


def _norm(text: str) -> str:
    return " ".join(str(text or "").split()).casefold()


def _coverage_lines(res, raw: str) -> list[str]:
    """Return raw OCR lines that are not already represented by Smart output."""
    represented = []
    if res.title:
        represented.append(res.title)
    if res.subtitle:
        represented.append(res.subtitle)
    for a, b in res.rows:
        represented.extend((a, b))
    represented.extend(res.other)
    have = {_norm(x) for x in represented if _norm(x)}
    extra = []
    for line in str(raw or "").splitlines():
        line = " ".join(line.split()).strip()
        if not line or _norm(line) in have:
            continue
        # Keep real text, not a line made only from punctuation/numbers.
        compact = re.sub(r"\s+", "", line)
        if len(compact) < 2 or sum(ch.isalpha() for ch in compact) < 2:
            continue
        if _norm(line) not in {_norm(x) for x in extra}:
            extra.append(line)
    return extra


def install(app):
    """Install lossless full-image OCR behavior without replacing the existing UI."""
    if getattr(app, "_complete_ocr_installed", False):
        return

    original_smart = app.smart

    def smart(img, min_pairs=3):
        # A full screenshot is never constrained by a reference pair count.
        # Selected areas can still pass their own min_pairs when needed.
        result = original_smart(img, 1 if min_pairs >= 3 else min_pairs)
        try:
            raw = ocr_engine.read_raw(img, app.codes()[0])
            # Prefer the richer raw pass as the complete source of truth.
            if len(raw.splitlines()) > len(result.raw.splitlines()):
                result.raw = raw
            missing = _coverage_lines(result, result.raw)
            if missing:
                result.other = list(result.other) + missing
        except Exception:
            pass
        return result

    app.smart = smart
    app._complete_ocr_installed = True
