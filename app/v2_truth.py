"""OCR truth and coverage safeguards for CharlieMJ OCR Studio v2.

This module wraps the existing deterministic layout pipeline instead of
replacing it. OCR observations are snapshotted before Smart/AI presentation,
and conservative geometry recovery restores vocabulary pairs missed by the
primary pairing pass.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class OCRTruthItem:
    """Immutable OCR observation used for coverage accounting."""
    text: str
    confidence: float
    line: int


@dataclass(frozen=True)
class OCRCoverage:
    """Counts describing how completely OCR observations are represented."""
    detected: int
    represented: int
    unrepresented: int
    recovered_pairs: int

    @property
    def complete(self) -> bool:
        """Return True when every OCR observation is represented."""
        return self.unrepresented == 0


def _norm(text: str) -> str:
    """Normalize text for identity comparison without changing displayed OCR."""
    return re.sub(r"\s+", " ", str(text).strip()).casefold()


def _is_text_segment(seg) -> bool:
    """Reject obvious symbol-only fragments from vocabulary coverage accounting."""
    text = str(getattr(seg, "text", "")).strip()
    compact = re.sub(r"\s+", "", text)
    if len(compact) < 2:
        return False
    return sum(ch.isalpha() for ch in compact) >= max(2, int(len(compact) * 0.45))


def _strong_vertical_pairs(segs):
    """Recover stacked OCR pairs with conservative geometry and one-to-one matching."""
    candidates = []
    for i, a in enumerate(segs):
        if not _is_text_segment(a):
            continue
        for j in range(i + 1, len(segs)):
            b = segs[j]
            if not _is_text_segment(b) or b.y0 < a.y0:
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
    return (_norm(pair[0]), _norm(pair[1]))


def reconcile_result(result, words, lang: str = ""):
    """Attach immutable OCR truth and recover missing bilingual pairs.

    The recovery pass uses the same segment geometry as the layout engine but
    does not mutate or replace the primary result rows. Only genuinely missing
    pairs are appended to bilingual results.
    """
    from app.layout import build_segments

    raw_segs = build_segments(list(words)) if words else []
    truth = tuple(
        OCRTruthItem(str(s.text), float(getattr(s, "conf", 0.0)), int(getattr(s, "line", 0)))
        for s in raw_segs
        if str(getattr(s, "text", "")).strip()
    )

    rows = list(getattr(result, "rows", []) or [])
    existing_pairs = {_row_key(p) for p in rows}
    existing_text = {_norm(x) for pair in rows for x in pair}
    recovered = []

    # Prefer the public layout pairing algorithm first. It is already tuned to
    # the application's OCR geometry; the fallback is deliberately stricter.
    try:
        from app.layout import vertical_pairs
        candidates = vertical_pairs(raw_segs)
    except Exception:
        candidates = []
    if not candidates:
        candidates = _strong_vertical_pairs(raw_segs)
    else:
        candidates = list(candidates) + [p for p in _strong_vertical_pairs(raw_segs) if _row_key(p) not in {_row_key(x) for x in candidates}]

    for a, b in candidates:
        pair = (str(a.text).strip(), str(b.text).strip())
        key = _row_key(pair)
        if key in existing_pairs:
            continue
        # A source phrase already represented on either side of an existing row
        # must not be paired again with unrelated text.
        if _norm(pair[0]) in existing_text or _norm(pair[1]) in existing_text:
            continue
        recovered.append(pair)
        existing_pairs.add(key)
        existing_text.update((_norm(pair[0]), _norm(pair[1])))

    if recovered and getattr(result, "kind", "") == "bilingual":
        result.rows.extend(recovered)
        rows = list(result.rows)

    represented_text = {_norm(x) for pair in rows for x in pair}
    unrepresented = sum(
        1 for item in truth
        if _is_text_segment(item)
        and _norm(item.text) not in represented_text
    )
    result.ocr_truth = truth
    result.coverage = OCRCoverage(
        detected=len(truth),
        represented=len(truth) - unrepresented,
        unrepresented=unrepresented,
        recovered_pairs=len(recovered),
    )
    result.recovered_pairs = tuple(recovered)
    return result


def install():
    """Install the safeguards around layout.analyze/merge_missing once."""
    from app import layout
    if getattr(layout, "_v2_truth_installed", False):
        return

    original_analyze = layout.analyze
    original_merge = layout.merge_missing

    def analyze_v2(words, lang="Turkish", *args, **kwargs):
        """Run the original analyzer, then enforce immutable OCR coverage."""
        word_list = list(words or [])
        result = original_analyze(word_list, lang, *args, **kwargs)
        return reconcile_result(result, word_list, lang)

    def merge_missing_v2(md, rows, extra=()):
        """Preserve every OCR row while retaining the original AI merge behavior."""
        merged, added = original_merge(md, rows, extra)
        return merged, added

    layout.analyze = analyze_v2
    layout.merge_missing = merge_missing_v2
    layout._v2_truth_installed = True
