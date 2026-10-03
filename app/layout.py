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

v1.2 additions
    * _consistent    : drops caption / footer "pairs" (too wide or unaligned) from the table
    * _bands/_heading: rows of the grid; the heading must be ALONE in the first row (a watermark or
                       a big word inside the grid is no longer mistaken for the title)
    * _fill          : recovers table cells the first OCR pass missed - it infers the grid (column
                       centres, row pitch) from the cells that WERE found and re-reads the empty spots
    * drop_noise     : also removes phone / social-media chrome ("Posts", "20 hours ago", "more")
    * full_text      : RAW mode text - every word, nothing filtered
    * to_notes       : study-notes Markdown for the editor (# title, ## Vocabulary, - **word** — meaning)
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
_EDGE_JUNK = " \t|~_—–-•·<>[]{}()\"'`“”‘"


def clean_text(t: str) -> str:
    """Trim stray symbols that OCR invents at the edges of a fragment."""
    return re.sub(r"\s+", " ", t.strip(_EDGE_JUNK)).strip()


_UI_RE = re.compile(
    r"^(posts?|reels?|stories|home|search|explore|follow(ing|ers)?|likes?|comments?|share|send|more|save|reply|translate|"
    r"\d+\s*(seconds?|minutes?|hours?|days?|weeks?|[smhdw])\s*(ago)?|(\d+\s*)+)$", re.I)


def drop_noise(segs, min_conf: float = 45.0):
    """Remove fragments that are unlikely to be real text (icons, UI symbols)."""
    keep = []
    med = statistics.median(x.h for x in segs) if segs else 0
    for s in segs:
        s.text = clean_text(s.text)
        if med and s.h > 2.2 * med and s.conf < 80:
            continue                                   # big shaky text = watermark / decoration
        compact = s.text.replace(" ", "")
        if _UI_RE.match(s.text.strip()):
            continue                                   # "Posts", "20 hours ago", "more" ...
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
            if gap < -0.3 * a.h or gap > 1.2 * min(a.h, b.h):
                continue                               # not directly below / too far
            if max(a.h, b.h) > 2.0 * min(a.h, b.h):
                continue                               # very different text size -> not a label pair
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


# ------------------------------------------------------------------- 5. grid helpers
def _pw(p):
    """Width of a pair (both texts together)."""
    return max(p[0].x1, p[1].x1) - min(p[0].x0, p[1].x0)


def _pc(p):
    """Horizontal centre of a pair."""
    return (min(p[0].x0, p[1].x0) + max(p[0].x1, p[1].x1)) / 2


def _consistent(pairs):
    """Drop 'pairs' that do not belong to the table: captions, footers, stray UI text.

    Normal-sized, confident pairs are kept. A pair is only questioned when it is unusually
    wide (a caption line) or has low confidence - and then it must line up (left / centre /
    right edge) with another pair, as real table cells do.
    """
    if len(pairs) < 4:
        return pairs
    mw = statistics.median(_pw(p) for p in pairs)
    keep = [p for p in pairs if 0.15 * mw <= _pw(p) <= 2.3 * mw]
    feats = [(min(a.x0, b.x0), _pc((a, b)), max(a.x1, b.x1)) for a, b in keep]
    tol = 0.25 * mw

    def aligned(i):
        return any(abs(feats[i][k] - feats[j][k]) <= tol for j in range(len(keep)) if j != i for k in range(3))
    out = [p for i, p in enumerate(keep)
           if (_pw(p) < 1.6 * mw and (p[0].conf + p[1].conf) / 2 >= 50) or aligned(i)]
    return out if len(out) >= 3 else pairs


def _cluster(values, tol):
    """Group sorted numbers that are within tol of their neighbour -> [(mean, count)]."""
    groups = []
    for v in sorted(values):
        if groups and v - groups[-1][-1] <= tol:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [(statistics.fmean(g), len(g)) for g in groups]


def _bands(pairs, unit):
    """Group pairs into rows (bands), top to bottom; each row sorted left to right."""
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
    return [sorted(b, key=lambda p: min(p[0].x0, p[1].x0)) for b in bands]


def _heading(bands):
    """A much larger pair ALONE in the first row (and followed by rows) is the heading.

    Cells inside a grid row can never be the heading, so a watermark or a big word in the
    middle of the table is not mistaken for a title any more.
    """
    if len(bands) < 3 or len(bands[0]) != 1:
        return None
    p = bands[0][0]
    rest = statistics.median(max(a.h, b.h) for band in bands[1:] for a, b in band)
    if max(p[0].h, p[1].h) >= 1.5 * rest and (p[0].conf + p[1].conf) / 2 >= 70:
        bands.pop(0)
        return tuple(sorted(p, key=lambda s: s.y0))
    return None


def _good_line(t, conf):
    t = clean_text(t)
    c = t.replace(" ", "")
    return len(c) >= 2 and conf >= 50 and sum(ch.isalpha() for ch in c) / len(c) >= 0.6


def _fill(bands, read_cell, lang, unit):
    """Recover table cells that the first OCR pass missed.

    The grid is inferred from the cells that WERE found: their column centres and row
    spacing. For every empty (row, column) position - including whole rows that are
    missing between two found rows - the label area is cropped and read again with
    read_cell(box) -> [(text, confidence), ...].
    """
    allp = [p for b in bands for p in b]
    mw = statistics.median(_pw(p) for p in allp)
    cols = [c for c, n in _cluster([_pc(p) for p in allp], 0.5 * mw) if n >= max(2, 0.4 * len(bands))]
    if len(cols) < 2:
        return bands, []
    tops = [statistics.median(min(a.y0, b.y0) for a, b in bd) for bd in bands]
    bots = [statistics.median(max(a.y1, b.y1) for a, b in bd) for bd in bands]
    height = statistics.median(b - t for t, b in zip(tops, bots))
    rows = list(zip(tops, bots, bands))
    diffs = [b - a for a, b in zip(tops, tops[1:])]
    if diffs:
        pitch = statistics.median(diffs)
        out = []
        for k, (t, b, band) in enumerate(rows):
            out.append((t, b, band))
            if k + 1 < len(rows):
                miss = round((tops[k + 1] - t) / pitch) - 1
                if miss >= 1 and tops[k + 1] - t > 1.7 * pitch:
                    out += [(t + pitch * m, t + pitch * m + height, []) for m in range(1, miss + 1)]
        rows = out
    top_is_orig = sum(a.cy < b.cy for a, b in allp) >= len(allp) / 2
    result, boxes = [], []
    for t, b, band in rows:
        band = list(band)
        for c in cols:
            if any(abs(_pc(p) - c) <= 0.5 * mw for p in band):
                continue
            box = (c - 0.55 * mw, t - 0.3 * unit, c + 0.55 * mw, b + 0.3 * unit)
            lines = [(x, cf) for x, cf in read_cell(box) if _good_line(x, cf)]
            if len(lines) < 2:
                continue
            (t1, c1), (t2, c2) = lines[0], lines[1]
            mid = (t + b) / 2
            s1 = Seg(clean_text(t1), c - 0.5 * mw, t, c + 0.5 * mw, mid, unit, c1, -1)
            s2 = Seg(clean_text(t2), c - 0.5 * mw, mid, c + 0.5 * mw, b, unit, c2, -1)
            sc = target_score(s1.text, lang) - target_score(s2.text, lang)
            first_orig = (sc > 0) if sc else top_is_orig
            band.append((s1, s2) if first_orig else (s2, s1))
            boxes.append(box)
        if band:
            result.append(sorted(band, key=lambda p: min(p[0].x0, p[1].x0)))
    return result, boxes


# ------------------------------------------------------------------- 6. analyze
def analyze(words, lang: str = "Turkish", min_conf: float = 45.0, refine=None, read_cell=None) -> Result:
    """Main entry: OCR words -> Result (title, table rows, leftovers, clean text).

    refine:    optional refine(seg, role) -> str, role "orig" / "trans". Re-reads one cell
               with the right single-language model (better for ş ı ğ ç).
    read_cell: optional read_cell(box) -> [(text, conf)]. Re-reads a missing grid cell.
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
    pairs = _consistent(pairs)

    if len(pairs) >= 3 and 2 * len(pairs) >= 0.5 * len(segs):
        res.kind = "bilingual"
        pairs = _orient(pairs, lang)
        used = {id(s) for p in pairs for s in p}
        bands = _bands(pairs, unit)
        head = _heading(bands)
        if head:
            res.title, res.subtitle = head[0].text, head[1].text
            used.update(id(s) for s in head)
        if refine:                                       # second, language-specific reading of each cell
            for a, b in (p for band in bands for p in band):
                for seg, role in ((a, "orig"), (b, "trans")):
                    try:
                        seg.text = clean_text(refine(seg, role) or seg.text)
                    except Exception:
                        pass
        boxes = []
        if read_cell:
            try:
                bands, boxes = _fill(bands, read_cell, lang, unit)
            except Exception:
                pass
        res.rows = [(a.text, b.text) for band in bands for a, b in band]
        def in_box(s):
            return any(b[0] <= (s.x0 + s.x1) / 2 <= b[2] and b[1] <= s.cy <= b[3] for b in boxes)
        left = [s for s in sorted(segs, key=lambda s: (s.cy, s.x0)) if id(s) not in used and not in_box(s)]
        top = rows_top([p for band in bands for p in band])
        if not res.title and top is not None:
            # a heading is clearly bigger than the labels - or only a bit bigger but sitting right above the first row
            big = [s for s in left if s.y1 <= top + 0.5 * unit and s.conf >= 70
                   and (s.h >= 1.6 * unit or (s.h >= 1.25 * unit and top - s.y1 <= 3 * unit))]
            if big:
                h = max(big, key=lambda s: s.h)
                res.title = h.text
                left.remove(h)
                # the line right under the title (smaller, overlapping horizontally) is the subtitle
                subs = [s for s in left if -0.3 * h.h <= s.y0 - h.y1 <= 1.2 * min(h.h, s.h) and s.h <= h.h
                        and min(s.x1, h.x1) - max(s.x0, h.x0) > 0.3 * min(s.w, h.w)]
                if subs:
                    sub = min(subs, key=lambda s: s.y0 - h.y1)
                    res.subtitle = sub.text
                    left.remove(sub)
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


def full_text(words) -> str:
    """RAW mode: every word, nothing removed or reordered by guesswork.

    Reading-order lines; text blocks that sit side by side are separated by 4 spaces.
    """
    lines = {}
    for s in sorted(build_segments(list(words)), key=lambda s: (s.line, s.x0)):
        lines.setdefault(s.line, []).append(s.text)
    return "\n".join("    ".join(v) for _, v in sorted(lines.items()))


def text_notes(md: str, heading: str) -> str:
    """Notes Markdown for plain text: a '## heading' followed by one paragraph per non-empty line."""
    body = [ln.strip() for ln in md.splitlines() if ln.strip()]
    return "\n".join([f"## {heading}", *body]) if body else ""


def to_notes(res: Result, md: str) -> str:
    """Study-notes Markdown for the text editor (headings + bullets by default).

        # Main title            <- big heading found in the picture
        ### Subtitle
        ## Vocabulary
        - **original** — translation

    Pairs are read back from `md` (the table the user sees and may have edited or swapped).
    """
    pairs = extract_pairs(md)
    if res is not None and res.kind == "bilingual" and pairs:
        out = []
        if res.title:
            out.append(f"# {res.title}")
        if res.subtitle:
            out.append(f"### {res.subtitle}")
        out.append("## Vocabulary")
        out += [f"- **{a}** — {b}" for a, b in pairs]
        return "\n".join(out)
    return text_notes(md, "Text")
