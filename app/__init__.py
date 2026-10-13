"""Charlie MJ OCR & Language Studio - application package (v2.0).

The v2 release preserves the existing OCR/layout foundation and adds lossless
OCR-truth reconciliation, selector selection history, and regression coverage.

Modules:
    config      - portable settings and constants
    layout      - OCR word geometry -> table/title/text plus Markdown notes
    ocr_engine  - Tesseract wrapper and RAW/deep OCR passes
    v2_truth    - immutable OCR observations and coverage safeguards
    richtext    - document model and exporters
    editor      - rich text editor
    selector    - zoom/pan/crop and multi-area selection with undo/redo
    local_ai    - optional localhost Ollama integration
    ui          - main application window and OCR queue
"""
from __future__ import annotations

import difflib
import re

__version__ = "2.0.0"


def _install_lossless_merge():
    """Install the deterministic OCR-pair merge guard without changing layout geometry."""
    from . import layout

    if getattr(layout, "_lossless_merge_installed", False):
        return

    original = layout.merge_missing

    def norm(text):
        return re.sub(r"\s+", " ", str(text).strip()).casefold()

    def pair_similarity(a, b):
        """Require both OCR columns to survive an AI rewrite."""
        left = difflib.SequenceMatcher(None, norm(a[0]), norm(b[0])).ratio()
        right = difflib.SequenceMatcher(None, norm(a[1]), norm(b[1])).ratio()
        return min(left, right)

    def merge_missing(md, rows, extra=()):
        """Append every OCR pair absent from AI markdown and return the exact count."""
        existing = layout.extract_pairs(md)
        candidates = []
        seen = set()
        for pair in list(extra or ()) + list(rows or ()):
            if not pair or len(pair) < 2:
                continue
            key = (norm(pair[0]), norm(pair[1]))
            if (not key[0] and not key[1]) or key in seen:
                continue
            seen.add(key)
            candidates.append((str(pair[0]).strip(), str(pair[1]).strip()))

        missing = [
            pair for pair in candidates
            if not any(pair_similarity(pair, have) >= 0.80 for have in existing)
        ]
        if not missing:
            return md, 0

        block = "\n".join(f"- **{a}** — {b}" for a, b in missing)
        return (
            md.rstrip() + "\n\n## More vocabulary (from OCR)\n" + block,
            len(missing),
        )

    layout.merge_missing = merge_missing
    layout._lossless_merge_installed = True


_install_lossless_merge()
