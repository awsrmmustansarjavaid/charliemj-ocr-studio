"""OCR truth and coverage safeguards for CharlieMJ OCR Studio v2.

This module is deliberately independent from Tesseract and Ollama.  It wraps
 the existing deterministic layout pipeline instead of replacing it, and keeps
an immutable snapshot of everything the OCR engine reported before Smart/AI
post-processing can filter or rewrite anything.

The key rule is simple: AI may improve presentation, but it may never delete
an OCR-detected item.  A second conservative geometry pass also recovers pairs
that the primary layout pass failed to pair.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class OCRTruthItem:
    """Immutable OCR observation used for coverage accounting."""
    text: str
    confidence: float
    line: int


@dataclass(frozen=True)
class OCRCoverage:
    """Counts describing what happened to the OCR source text."""
    detected: int
    represented: int
    unrepresented: int
    recovered_pairs: int

    @property
    def complete(self) -> bool:
        """Return True when every detected source item has a representation."""
        return self.unrepresented == 0


def _norm(text: str) -> str:
    """Normalize text only for duplicate detection; never alter displayed OCR."""
    return re.sub(r"\s+", " ", str(text).strip()).casefold()


def _is_text_segment(seg) -> bool:
    """Reject obvious UI/symbol fragments without changing the original OCR list."""
    t = getattr(seg, "text", "").strip()
    compact = re.sub(r"\s+", "", t)
    if len(compact) < 2:
        return False
    return sum(ch.isalpha() for ch in compact) >= max(2, int(len(compact) * 0.45))


def _strong_vertical_pairs(segs):
    """Recover obvious stacked pairs missed by the primary pairing thresholds."""
    candidates = []
    for i, a in enumerate(segs):
        if not _is_text_segment(a):
            continue
        for j, b in enumerate(segs):
            if i == j or not _is_text_segment(b):
                continue
            if b.y0 < a.y0:
                continue
            gap = b.y0 - a.y1
            unit = max(1.0, min(a.h, b.h))
            if gap < -0.25 * unit or gap > 1.0 * unit:
                continue
            overlap = min(a.x1, b.x1) - max(a.x0, b.x0)
            if overlap < 0.40 * min(a.w, b.w):
                continue
            if max(a.h, b.h) > 2.3 * min(a.h, b.h):
                continue
            conf = (a.conf + b.conf) / 2.0
            if conf < 35:
                continue
            candidates.append((gap, -conf, i, j))
    used = set()
    out = []
    for _, _, i, j in sorted(candidates):
        if i in used or j in used:
            continue
        used.update((i, j))
        out.append((segs[i], segs[j]))
    return out


def _row_key(pair):
    """Return a case-insensitive identity for a vocabulary pair."""
    return (_norm(pair[0]), _norm(pair[1]))


def reconcile_result(result, words, lang: str = ""):
    """Attach OCR-truth and conservatively recover missing vocabulary pairs.

    The original result is retained.  Only pairs that are geometrically strong
    and not already represented are appended.  All source observations are
    stored separately, so filtering for UI chrome cannot erase OCR truth.
    """
    # Import lazily so importing this module never creates an OCR/GUI dependency.
    from app.layout import build_segments

    raw_segs = build_segments(list(words)) if words else []
    truth = tuple(
        OCRTruthItem(str(s.text), float(getattr(s, "conf", 0.0)), int(getattr(s, "line", 0)))
        for s in raw_segs if str(getattr(s, "text", "")).strip()
    )

    existing = {_norm(a) for a, _ in getattr(result, "rows", [])}
    existing_pairs = {_row_key(p) for p in getattr(result, "rows", [])}
    recovered = []
    for a, b in _strong_vertical_pairs(raw_segs):
        key = _row_key((a.text, b.text))
        if key in existing_pairs:
            continue
        if _norm(a.text) in existing or _norm(b.text) in existing:
            continue
        recovered.append((a.text.strip(), b.text.strip()))
        existing_pairs.add(key)
        existing.update((_norm(a.text), _norm(b.text)))

    # Only add recovered pairs to bilingual results.  Plain-text OCR remains plain text.
    if recovered and getattr(result, "kind", "") == "bilingual":
        result.rows.extend(recovered)

    represented_text = set(existing)
    unrepresented = sum(1 for item in truth if _norm(item.text) not in represented_text and _is_text_segment(next((s for s in raw_segs if _norm(s.text) == _norm(item.text)), item)))
    result.ocr_truth = truth
    result.coverage = OCRCoverage(len(truth), len(truth) - unrepresented, unrepresented, len(recovered))
    result.recovered_pairs = tuple(recovered)
    return result


def install():
    """Install the v2 safeguards around the existing layout functions once."""
    from app import layout
    if getattr(layout, "_v2_truth_installed", False):
        return

    original_analyze = layout.analyze
    original_merge = layout.merge_missing

    def analyze_v2(words, lang, *args, **kwargs):
        """Run the original analyzer, then enforce immutable OCR coverage."""
        word_list = list(words or [])
        result = original_analyze(word_list, lang, *args, **kwargs)
        return reconcile_result(result, word_list, lang)

    def merge_missing_v2(md, rows, extra=()):
        """Preserve every OCR row while retaining the original AI merge behavior."""
        merged, added = original_merge(md, rows, extra)
        # A second deterministic pass prevents a future AI parser from silently
        # dropping rows that were supplied by the OCR source.
        present = {_norm(a) for a, _ in _extract_pairs(merged)}
        missing = []
        for a, b in list(extra) + list(rows):
            if _norm(a) not in present:
                missing.append((a, b))
                present.add(_norm(a))
        if missing:
            merged = merged.rstrip() + "\n\n## More vocabulary (from OCR truth)\n" + "\n".join(
                f"- **{a}** — {b}" for a, b in missing
            )
            added += len(missing)
        return merged, added

    def _extract_pairs(md):
        try:
            return layout.extract_pairs(md)
        except Exception:
            return []

    layout.analyze = analyze_v2
    layout.merge_missing = merge_missing_v2
    layout._v2_truth_installed = True
