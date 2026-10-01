"""
layout.py - turn OCR words + coordinates into clean, structured learning output.

Why this module exists
----------------------
Plain OCR returns one long string and LOSES the relationship between words
(for example a Turkish label and the English label printed under it).
Here we keep the word coordinates and rebuild that relationship with simple,
deterministic geometry - no AI, no guessing, no invented text.

Pipeline (all functions are pure Python, so they are easy to unit-test):

    words -> build_segments() -> drop_noise() -> find pairs -> analyze() -> to_markdown()

    * build_segments : group words into lines, then split lines at large gaps
                       (this separates the 4 columns of a card grid)
    * drop_noise     : remove low-confidence / symbol-only fragments
    * pairs          : "vertical" (label above translation) or
                       "horizontal" (two-column table row)
    * analyze        : decide the content type and orientation (which side is
                       the learning language) and return a Result
    * to_markdown    : render an aligned Markdown table (or clean text)
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- data


@dataclass
class Word:
    """One OCR word with its bounding box (pixels) and confidence (0-100)."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 100.0

    @property
    def h(self) -> float:
        return max(1.0, self.y1 - self.y0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Seg:
    """A run of words on one line with no big gap inside (e.g. one card label)."""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    h: float          # typical text height (median of its words)
    conf: float       # mean confidence
    line: int = 0     # index of the text line it came from

    @property
    def w(self) -> float:
        return max(1.0, self.x1 - self.x0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Result:
    """Structured output of analyze()."""
    kind: str = "empty"                 # "bilingual" | "text" | "empty"
    title: str = ""
    subtitle: str = ""
    rows: list = field(default_factory=list)    # [(original, translation), ...]
    other: list = field(default_factory=list)   # leftover text (unpaired)
    lines: list = field(default_factory=list)   # clean text lines (kind == "text")
    raw: str = ""                       # plain reading-order text
    confidence: float = 0.0             # mean word confidence
    method: str = ""                    # "vertical" | "horizontal" | ""


# ------------------------------------------------------------------- 1. segments
def build_segments(words, gap_factor: float = 1.1):
    """Group words into lines, then split each line into segments at wide gaps.

    gap_factor: a gap wider than gap_factor x text height starts a new segment.
    Words inside a phrase are ~0.3 x height apart; columns are usually > 1.5 x.
    """
    words = [w for w in words if w.text.strip()]
    words.sort(key=lambda w: (w.cy, w.x0))
    lines = []  # each: {"cy", "h", "w": [words]}
    for w in words:
        for ln in lines:
            if abs(w.cy - ln["cy"]) <= 0.4 * max(w.h, ln["h"]):
                ln["w"].append(w)
                ln["cy"] = statistics.fmean(x.cy for x in ln["w"])
                ln["h"] = max(ln["h"], w.h)
                break
        else:
            lines.append({"cy": w.cy, "h": w.h, "w": [w]})
    lines.sort(key=lambda ln: ln["cy"])

    segs = []
    for li, ln in enumerate(lines):
        ws = sorted(ln["w"], key=lambda x: x.x0)
        limit = gap_factor * statistics.median(x.h for x in ws)
        group = [ws[0]]
        for prev, cur in zip(ws, ws[1:]):
            if cur.x0 - prev.x1 > limit:      # big gap -> new segment
                segs.append(_make_seg(group, li))
                group = []
            group.append(cur)
        segs.append(_make_seg(group, li))
    return segs


def _make_seg(ws, line):
    return Seg(" ".join(w.text for w in ws), min(w.x0 for w in ws), min(w.y0 for w in ws),
               max(w.x1 for w in ws), max(w.y1 for w in ws),
               statistics.median(w.h for w in ws), statistics.fmean(w.conf for w in ws), line)


# ------------------------------------------------------------------- 2. noise
_EDGE_JUNK = " \t|~_—–-•·<>[]{}()\"'`"


def clean_text(t: str) -> str:
    """Trim stray symbols that OCR invents at the edges of a fragment."""
    return re.sub(r"\s+", " ", t.strip(_EDGE_JUNK)).strip()


def drop_noise(segs, min_conf: float = 45.0):
    """Remove fragments that are unlikely to be real text (icons, UI symbols)."""
    keep = []
    for s in segs:
        s.text = clean_text(s.text)
        compact = s.text.replace(" ", "")
        if len(compact) < 2 or s.conf < min_conf:
            continue
        if sum(c.isalpha() for c in compact) / len(compact) < 0.6:
            continue                                   # mostly digits/symbols
        toks = s.text.split()
        if len(toks) > 1 and all(len(t) <= 1 for t in toks):
            continue                                   # e.g. "O Q G"
        keep.append(s)
    return keep


# ------------------------------------------------------------------- 3. language hints
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
_EN_WORDS = {"the", "of", "and", "to", "in", "for", "is", "are", "with", "my", "your", "you", "what",
             "how", "gloves", "types", "hello", "good", "morning", "winter", "work", "sports"}


def target_score(text: str, lang: str) -> int:
    """Positive = looks like the language being LEARNED, negative = looks like English/other.

    Scripts (Arabic/Urdu/Persian) are decisive. For Turkish we use its special
    letters; for English we use a few common words. A score of 0 means "unknown"
    and the caller falls back to position (upper/left = original).
    """
    is_ar = bool(_ARABIC.search(text))
    if lang in ("Urdu", "Arabic", "Persian"):
        return 5 if is_ar else -5
    if is_ar:
        return -5
    words = re.findall(r"[^\W\d_]+", text.lower())
    en = sum(w in _EN_WORDS for w in words)
    if lang == "Turkish":
        return 2 * sum(c in _TR_CHARS for c in text) - en
    if lang == "English":
        return en
    return 0


# ------------------------------------------------------------------- 4. pairing
def vertical_pairs(segs):
    """Pair each segment with the nearest one directly BELOW it (label + translation)."""
    cands = []
    for i, a in enumerate(segs):
        for j, b in enumerate(segs):
            if i == j:
                continue
            gap = b.y0 - a.y1
            if gap < -0.3 * a.h or gap > 1.0 * max(a.h, b.h):
                continue                               # not directly below / too far
            overlap = min(a.x1, b.x1) - max(a.x0, b.x0)
            if overlap < 0.35 * min(a.w, b.w):
                continue                               # not in the same column
            cands.append((gap, i, j))
    used, pairs = set(), []
    for gap, i, j in sorted(cands):                    # closest first, one-to-one
        if i not in used and j not in used:
            used.update((i, j))
            pairs.append((segs[i], segs[j]))
    return pairs


def horizontal_pairs(segs):
    """Pair the two segments of a line that has exactly two (a two-column table row)."""
    by_line = {}
    for s in segs:
        by_line.setdefault(s.line, []).append(s)
    pairs = []
    for row in by_line.values():
        if len(row) == 2:
            row.sort(key=lambda s: s.x0)
            pairs.append((row[0], row[1]))
    return pairs


def _orient(pairs, lang):
    """Decide (original, translation) for every pair, consistently across the image."""
    decided, first_wins = [], 0
    for a, b in pairs:
        sa, sb = target_score(a.text, lang), target_score(b.text, lang)
        decided.append((sa > sb) - (sa < sb))          # +1: a is original, -1: b, 0: unknown
    votes = [d for d in decided if d]
    first_is_original = (sum(1 for d in votes if d > 0) >= sum(1 for d in votes if d < 0)) if votes else True
    out = []
    for (a, b), d in zip(pairs, decided):
        if d == 0:
            d = 1 if first_is_original else -1         # tie -> follow the majority position
        out.append((a, b) if d > 0 else (b, a))
    return out


def _reading_order(pairs, unit):
    """Sort pairs row by row (top to bottom), left to right inside a row."""
    pairs = sorted(pairs, key=lambda p: min(p[0].cy, p[1].cy))
    bands, cur, top = [], [], None
    for p in pairs:
        y = min(p[0].y0, p[1].y0)
        if top is None or y - top > 1.5 * unit:
            if cur:
                bands.append(cur)
            cur, top = [], y
        cur.append(p)
    if cur:
        bands.append(cur)
    return [p for band in bands for p in sorted(band, key=lambda p: min(p[0].x0, p[1].x0))]


# ------------------------------------------------------------------- 5. analyze
def analyze(words, lang: str = "Turkish", min_conf: float = 45.0, refine=None) -> Result:
    """Main entry: OCR words -> Result (title, table rows, leftovers, clean text).

    refine: optional callback refine(seg, role) -> str, role is "orig" or "trans".
    It lets the OCR layer re-read each table cell on its own with the right
    language model (much better for Turkish letters like ş ı ğ ç).
    """
    res = Result()
    all_segs = build_segments(list(words))
    if not all_segs:
        return res
    res.confidence = round(statistics.fmean(s.conf for s in all_segs), 1)
    res.raw = "\n".join(_join_lines(all_segs))
    segs = drop_noise(all_segs, min_conf)
    if not segs:
        return res
    unit = statistics.median(s.h for s in segs)

    vp, hp = vertical_pairs(segs), horizontal_pairs(segs)
    pairs, res.method = (vp, "vertical") if len(vp) >= len(hp) else (hp, "horizontal")

    if len(pairs) >= 3 and 2 * len(pairs) >= 0.5 * len(segs):
        res.kind = "bilingual"
        pairs = _orient(pairs, lang)
        # A much larger pair near the top is the heading, not a vocabulary row.
        sizes = statistics.median(max(a.h, b.h) for a, b in pairs)
        heads = [p for p in pairs if max(p[0].h, p[1].h) >= 1.35 * sizes]
        if heads:
            head = min(heads, key=lambda p: min(p[0].y0, p[1].y0))
            pairs.remove(head)
            first, second = sorted(head, key=lambda s: s.y0)
            res.title, res.subtitle = first.text, second.text
        if refine:                                      # re-read each TABLE cell with its own language
            for a, b in pairs:                          # (the big title keeps its first-pass text)
                a.text = refine(a, "orig") or a.text
                b.text = refine(b, "trans") or b.text
        pairs = _reading_order(pairs, unit)
        res.rows = [(a.text, b.text) for a, b in pairs]
        used = {id(s) for p in pairs for s in p}
        used.update(id(s) for s in ([] if not heads else [first, second]))
        left = [s for s in sorted(segs, key=lambda s: (s.cy, s.x0)) if id(s) not in used]
        if not res.title and rows_top(pairs) is not None:
            # a big, unpaired line above the first row is the heading (e.g. "Daily Greetings")
            big = [s for s in left if s.h >= 1.3 * unit and s.y1 <= rows_top(pairs) + 0.5 * unit]
            if big:
                head = max(big, key=lambda s: s.h)
                res.title = head.text
                left.remove(head)
        res.other = [s.text for s in left]
    else:
        res.kind = "text"
        res.lines = _paragraphs(segs, unit)
    return res


def rows_top(pairs):
    """Y coordinate of the top of the first table row (None when there are no rows)."""
    return min((min(a.y0, b.y0) for a, b in pairs), default=None)


def _join_lines(segs):
    """Reading-order plain text: one string per line, segments joined by spaces."""
    lines = {}
    for s in sorted(segs, key=lambda s: (s.line, s.x0)):
        lines.setdefault(s.line, []).append(s.text)
    return [" ".join(v) for _, v in sorted(lines.items())]


def _paragraphs(segs, unit):
    """Fallback for normal text: keep lines, insert a blank line at large vertical gaps."""
    out, prev_bottom = [], None
    for ln in sorted({s.line for s in segs}):
        row = sorted((s for s in segs if s.line == ln), key=lambda s: s.x0)
        top = min(s.y0 for s in row)
        if prev_bottom is not None and top - prev_bottom > 0.9 * unit:
            out.append("")
        out.append(" ".join(s.text for s in row))
        prev_bottom = max(s.y1 for s in row)
    return out


# ------------------------------------------------------------------- 6. output
def to_markdown(res: Result, orig_name: str = "Turkish", trans_name: str = "English", swap: bool = False) -> str:
    """Render a Result as Markdown. Tables are padded so they line up in a monospace box."""
    if res.kind == "empty":
        return "(no text found)"
    if res.kind == "text":
        return "\n".join(res.lines).strip()
    a_name, b_name = (trans_name, orig_name) if swap else (orig_name, trans_name)
    rows = [(b, a) if swap else (a, b) for a, b in res.rows]
    out = []
    if res.title:
        out.append(f"### {res.title}")
        if res.subtitle:
            out.append(f"*{res.subtitle}*")
        out.append("")
    w1 = max([len(a_name)] + [len(a) for a, _ in rows])
    w2 = max([len(b_name)] + [len(b) for _, b in rows])
    out.append(f"| {'#':>2} | {a_name:<{w1}} | {b_name:<{w2}} |")
    out.append(f"|{'-' * 4}|{'-' * (w1 + 2)}|{'-' * (w2 + 2)}|")
    for i, (a, b) in enumerate(rows, 1):
        out.append(f"| {i:>2} | {a:<{w1}} | {b:<{w2}} |")
    if res.other:
        out += ["", "**Other text:** " + " · ".join(res.other)]
    return "\n".join(out)


def status_line(res: Result, orig_name: str, trans_name: str) -> str:
    """One-line summary shown in the status bar after OCR."""
    if res.kind == "bilingual":
        return f"Bilingual table · {orig_name} → {trans_name} · {len(res.rows)} pairs · confidence {res.confidence:.0f}%"
    if res.kind == "text":
        return f"Clean text · {len(res.lines)} lines · confidence {res.confidence:.0f}%"
    return "No text found"


# ------------------------------------------------------------------- 7. pair extraction (for CSV)
_BULLET = re.compile(r"^\s*[-*]\s*\**(.+?)\**\s+[—–-]\s+(.+)$")


def extract_pairs(md: str):
    """Read (original, translation) pairs back out of Markdown text.

    Understands the numbered tables produced by to_markdown() and the
    '- **word** — meaning' bullets produced by the AI buttons, so exports
    also reflect anything the user edited by hand.
    """
    pairs = []
    for line in md.splitlines():
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].isdigit():
                pairs.append((cells[1], cells[2]))
            continue
        m = _BULLET.match(line)
        if m:
            pairs.append((m.group(1).strip(), m.group(2).strip()))
    return pairs


def to_plain(md: str) -> str:
    """Markdown -> plain text: no #, ** markers; table rows become 'word — meaning'."""
    out = []
    for line in md.splitlines():
        t = line.strip()
        if t.startswith("|"):
            cells = [c.strip() for c in t.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].isdigit():
                out.append(f"{cells[1]} — {cells[2]}")
            continue                                    # header / separator rows
        t = re.sub(r"^#{1,6}\s+", "", line)
        t = re.sub(r"\*+", "", t)
        out.append(re.sub(r"^\s*-\s+", "• ", t))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()
