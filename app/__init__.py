"""Charlie MJ OCR & Language Studio - application package (v2.3)."""
from __future__ import annotations

import difflib
import re

__version__ = "2.3.0"


def _lossless_norm(text):
    return re.sub(r"\s+", " ", str(text).strip()).casefold()


def _install_lossless_merge():
    """Install the deterministic OCR-pair merge guard without changing layout geometry."""
    from . import layout

    if getattr(layout, "_lossless_merge_installed", False):
        return

    original = layout.merge_missing

    def merge_missing(md, rows, extra=()):
        """Append every OCR pair absent from AI markdown and return the exact count."""
        existing = extract_pairs(md)
        candidates = []
        seen = set()
        for pair in list(extra or ()) + list(rows or ()):
            if not pair or len(pair) < 2:
                continue
            key = (_lossless_norm(pair[0]), _lossless_norm(pair[1]))
            if (not key[0] and not key[1]) or key in seen:
                continue
            seen.add(key)
            candidates.append((str(pair[0]).strip(), str(pair[1]).strip()))
        missing = []
        for pair in candidates:
            key = (_lossless_norm(pair[0]), _lossless_norm(pair[1]))
            if key not in existing:
                missing.append(pair)
                existing.add(key)
        if not missing:
            return md, 0
        block = "\n\n## More vocabulary (from OCR)\n\n" + "\n".join(f"- {a} — {b}" for a, b in missing)
        return (md.rstrip() + block).strip(), len(missing)

    layout.merge_missing = merge_missing
    # Some older modules imported the function directly; mutate its code object
    # rather than leaving a stale reference that can discard OCR rows.
    try:
        original.__code__ = merge_missing.__code__
        original.__defaults__ = merge_missing.__defaults__
    except Exception:
        pass
    layout._lossless_merge_installed = True


def extract_pairs(md):
    """Extract simple Markdown vocabulary rows for deterministic de-duplication."""
    pairs = set()
    for line in str(md or "").splitlines():
        m = re.match(r"^\s*[-*]\s+(.+?)\s+[—–-]\s+(.+?)\s*$", line)
        if m:
            pairs.add((_lossless_norm(m.group(1)), _lossless_norm(m.group(2))))
    return pairs


_install_lossless_merge()
