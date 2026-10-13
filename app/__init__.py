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
            preserved = False
            for have in existing:
                have_key = (_lossless_norm(have[0]), _lossless_norm(have[1]))
                if key == have_key:
                    preserved = True
                    break
                if (re.findall(r"\d+", key[0]) != re.findall(r"\d+", have_key[0]) or
                        re.findall(r"\d+", key[1]) != re.findall(r"\d+", have_key[1])):
                    continue
                if (len(key[0]) != len(have_key[0]) or len(key[1]) != len(have_key[1])):
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
        return md.rstrip() + "\n\n## More vocabulary (from OCR)\n" + block, len(missing)

    layout.__dict__["_lossless_norm"] = _lossless_norm
    layout.__dict__["difflib"] = difflib
    layout.__dict__["re"] = re
    original.__code__ = merge_missing.__code__
    original.__defaults__ = merge_missing.__defaults__
    original.__doc__ = merge_missing.__doc__
    layout.merge_missing = original
    layout._lossless_merge_installed = True


_install_lossless_merge()
