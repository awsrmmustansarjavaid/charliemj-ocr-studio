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

    def merge_missing(md, rows, extra=()):
        """Append every OCR pair absent from AI markdown and return the exact count."""
        existing = extract_pairs(md)

        # Normalize only whitespace/case. Pair identity remains two-dimensional:
        # both the source and translation must match. A conservative fuzzy check
        # is retained for same-length OCR substitutions, while length differences
        # prevent word1/word12-style false matches.
        def norm(text):
            return re.sub(r"\s+", " ", str(text).strip()).casefold()

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

        missing = []
        for pair in candidates:
            key = (norm(pair[0]), norm(pair[1]))
            preserved = False
            for have in existing:
                have_key = (norm(have[0]), norm(have[1]))
                if key == have_key:
                    preserved = True
                    break

                # Do not let numbered entries such as word12/meaning12 match
                # word1/meaning1 merely because SequenceMatcher scores highly.
                if (len(key[0]) != len(have_key[0]) or
                        len(key[1]) != len(have_key[1])):
                    continue
                left = difflib.SequenceMatcher(None, key[0], have_key[0]).ratio()
                right = difflib.SequenceMatcher(None, key[1], have_key[1]).ratio()
                if min(left, right) >= 0.80:
                    preserved = True
                    break
            if not preserved:
                missing.append(pair)

        if not missing:
            return md, 0

        block = "\n".join(f"- **{a}** — {b}" for a, b in missing)
        return (
            md.rstrip() + "\n\n## More vocabulary (from OCR)\n" + block,
            len(missing),
        )

    # Mutate the original function object as well as the module attribute. This
    # matters when another module imported merge_missing before package init
    # completed; those references must receive the same lossless behavior.
    layout.__dict__["extract_pairs"] = layout.extract_pairs
    original.__code__ = merge_missing.__code__
    original.__defaults__ = merge_missing.__defaults__
    original.__doc__ = merge_missing.__doc__
    layout.merge_missing = original
    layout._lossless_merge_installed = True


_install_lossless_merge()
