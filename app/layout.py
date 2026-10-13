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

import difflib
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
    h: float
    conf: float
    line: int = 0
    words: list = field(default_factory=list)
    padx: float = 0.0

    @property
    def w(self) -> float:
        return max(1.0, self.x1 - self.x0)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Result:
    """Structured output of analyze()."""
    kind: str = "empty"
    title: str = ""
    subtitle: str = ""
    rows: list = field(default_factory=list)
    other: list = field(default_factory=list)
    lines: list = field(default_factory=list)
    raw: str = ""
    confidence: float = 0.0
    method: str = ""
    unread: int = 0
    grid: tuple = None
    low: int = 0


# ------------------------------------------------------------------- 1. segments
def build_segments(words, gap_factor: float = 1.1):
    """Group words into lines, then split each line into segments at wide gaps."""
    words = [w for w in words if w.text.strip()]
    words.sort(key=lambda w: (w.cy, w.x0))
    lines = []
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
            if cur.x0 - prev.x1 > limit:
                segs.append(_make_seg(group, li))
                group = []
            group.append(cur)
        segs.append(_make_seg(group, li))
    return segs


def _make_seg(ws, line):
    return Seg(" ".join(w.text for w in ws), min(w.x0 for w in ws), min(w.y0 for w in ws),
               max(w.x1 for w in ws), max(w.y1 for w in ws),
               statistics.median(w.h for w in ws), statistics.fmean(w.conf for w in ws), line, list(ws))


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
            continue
        compact = s.text.replace(" ", "")
        if _UI_RE.match(s.text.strip()):
            continue
        if len(compact) < 2 or s.conf < min_conf:
            continue
        if sum(c.isalpha() for c in compact) / len(compact) < 0.6:
            continue
        toks = s.text.split()
        if len(toks) > 1 and all(len(t) <= 1 for t in toks):
            continue
        keep.append(s)
    return keep


# ------------------------------------------------------------------- 3. language hints
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")
_TR_CHARS = set("çğıöşüÇĞİÖŞÜ")
_EN_WORDS = {"the", "of", "and", "to", "in", "for", "is", "are", "with", "my", "your", "you", "what",
             "how", "gloves", "types", "hello", "good", "morning", "winter", "work", "sports"}


def target_score(text: str, lang: str) -> int:
    """Positive = looks like the language being LEARNED, negative = looks like English/other."""
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
                continue
            if max(a.h, b.h) > 2.0 * min(a.h, b.h):
                continue
            overlap = min(a.x1, b.x1) - max(a.x0, b.x0)
            if overlap < 0.35 * min(a.w, b.w):
                continue
            cands.append((gap, i, j))
    used, pairs = set(), []
    for gap, i, j in sorted(cands):
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
    decided = []
    for a, b in pairs:
        sa, sb = target_score(a.text, lang), target_score(b.text, lang)
        decided.append((sa > sb) - (sa < sb))
    votes = [d for d in decided if d]
    first_is_original = (sum(1 for d in votes if d > 0) >= sum(1 for d in votes if d < 0)) if votes else True
    out = []
    for (a, b), d in zip(pairs, decided):
        if d == 0:
            d = 1 if first_is_original else -1
        out.append((a, b) if d > 0 else (b, a))
    return out


# ------------------------------------------------------------------- 4b. card grid detection
def _centres(segs):
    rel = [s for s in segs if len(s.words) <= 3 and len(s.text.replace(" ", "")) >= 3]
    if len(rel) < 4:
        return None
    mw = statistics.median(s.w for s in rel)
    rows = {}
    for s in rel:
        rows.setdefault(s.line, []).append((s.x0 + s.x1) / 2)
    diffs = []
    for cs in rows.values():
        cs.sort()
        diffs += [b - a for a, b in zip(cs, cs[1:]) if b - a >= 0.8 * mw]
    if len(diffs) < 2:
        return None
    first = min(diffs)
    pitch = statistics.median([d for d in diffs if d <= 1.15 * first])
    xs = [(s.x0 + s.x1) / 2 for s in rel]
    def fits(c):
        return sum(abs((x - c) / pitch - round((x - c) / pitch)) < 0.12 for x in xs)
    origin = max(xs, key=fits)
    if fits(origin) < 4:
        return None
    lo, hi = min(s.x0 for s in segs), max(s.x1 for s in segs)
    c = origin
    while c - pitch >= lo - 0.2 * pitch:
        c -= pitch
    out = []
    while c <= hi + 0.2 * pitch:
        out.append(c)
        c += pitch
    return out, pitch


def _split_merged(segs, grid):
    if not grid:
        return segs
    centres, pitch = grid
    origin, out = centres[0], []
    for s in segs:
        if len(s.words) < 2:
            out.append(s)
            continue
        ws = sorted(s.words, key=lambda w: w.x0)
        h = statistics.median(w.h for w in ws)
        groups, prev = [[ws[0]]], ws[0]
        for w in ws[1:]:
            col = lambda x: round(((x.x0 + x.x1) / 2 - origin) / pitch)
            if col(w) != col(prev) and w.x0 - prev.x1 >= 0.5 * h:
                groups.append([])
            groups[-1].append(w)
            prev = w
        if len(groups) == 1:
            out.append(s)
            continue
        for g in groups:
            part = _make_seg(g, s.line)
            part.text = clean_text(part.text)
            out.append(part)
    return out


# ------------------------------------------------------------------- 5. grid helpers
def _pw(p):
    return max(p[0].x1, p[1].x1) - min(p[0].x0, p[1].x0)


def _pc(p):
    return (min(p[0].x0, p[1].x0) + max(p[0].x1, p[1].x1)) / 2


def _consistent(pairs):
    if len(pairs) < 4:
        return pairs
    mw = statistics.median(_pw(p) for p in pairs)
    keep = [p for p in pairs if 0.15 * mw <= _pw(p) <= 2.3 * mw]
    feats = [(min(a.x0, b.x0), _pc((a, b)), max(a.x1, b.x1)) for a, b in keep]
    if len(keep) < 4:
        return keep
    def aligned(i, j):
        return any(abs(feats[i][k] - feats[j][k]) <= 0.18 * mw for k in range(3))
    good = []
    for i, p in enumerate(keep):
        if sum(aligned(i, j) for j in range(len(keep)) if j != i) >= 1:
            good.append(p)
    return good or keep


def _bands(pairs, unit):
    bands = []
    for p in sorted(pairs, key=lambda q: min(q[0].y0, q[1].y0)):
        cy = (p[0].cy + p[1].cy) / 2
        for band in bands:
            if abs(cy - band[0]) <= 1.2 * unit:
                band[1].append(p)
                break
        else:
            bands.append([cy, [p]])
    return [sorted(b, key=lambda q: _pc(q)) for _, b in bands]


def _heading(bands):
    if not bands or len(bands[0]) != 1:
        return None
    return bands[0][0]


def _pick_lines(lines):
    good = [(x, cf) for x, cf in lines if len(str(x).strip()) >= 2 and cf >= 35]
    if len(good) <= 2:
        return good
    best = max(range(len(good) - 1), key=lambda k: good[k][1] + good[k + 1][1] + 0.1 * k)
    return good[best:best + 2]


def _lattice(bands, read_cell, lang, unit, size=None, y_min=0.0, deep=False):
    allp = [p for b in bands for p in b]
    mw = statistics.median(_pw(p) for p in allp)
    cols, pitch = _columns(allp, mw, size[0] if size else None)
    if len(cols) < 2:
        return bands, [], 0, None
    top_is_orig = sum(a.cy < b.cy for a, b in allp) >= len(allp) / 2
    tops = [statistics.median(min(a.y0, b.y0) for b in bd) for bd in bands]
    bots = [statistics.median(max(a.y1, b.y1) for a, b in bd) for bd in bands]
    height = statistics.median(b - t for t, b in zip(tops, bots))
    rows = list(zip(tops, bots, bands))
    step = statistics.median(b - a for a, b in zip(tops, tops[1:])) if len(tops) >= 2 else None
    if step:
        out = []
        for k, (t, b, band) in enumerate(rows):
            out.append((t, b, band))
            if k + 1 < len(rows) and tops[k + 1] - t > 1.7 * step:
                miss = round((tops[k + 1] - t) / step) - 1
                out += [(t + step * m, t + step * m + height, []) for m in range(1, miss + 1)]
        rows = out
    boxes, unread = [], 0
    def read_new(c, t, b):
        box = (c - 0.5 * pitch, t - 0.3 * unit, c + 0.5 * pitch, b + 0.3 * unit)
        lines = _pick_lines(read_cell(box))
        if len(lines) < 2:
            return None
        (t1, c1), (t2, c2) = lines
        mid = (t + b) / 2
        return (Seg(clean_text(t1), box[0], t, box[2], mid, unit, c1, -1),
                Seg(clean_text(t2), box[0], mid, box[2], b, unit, c2, -1), box)
    result = []
    for t, b, band in rows:
        band = list(band)
        for c in cols:
            mine = [p for p in band if abs(_pc(p) - c) <= 0.45 * pitch]
            if mine:
                got = read_new(c, t, b)
                if got:
                    top, bot = sorted(mine[0], key=lambda s: s.y0)
                    top.text, top.conf, bot.text, bot.conf = got[0].text, got[0].conf, got[1].text, got[1].conf
                continue
            got = read_new(c, t, b)
            if got is None:
                unread += 1
                continue
            band.append((got[0], got[1]))
            boxes.append(got[2])
        if band:
            result.append(sorted(band, key=lambda p: min(p[0].x0, p[1].x0)))
    flat = [(sorted(p, key=lambda s: s.y0)[0], sorted(p, key=lambda s: s.y0)[1]) for bd in result for p in bd]
    oriented = iter(_orient(flat, lang))
    result = [[next(oriented) for _ in bd] for bd in result]
    return result, boxes, unread, (len(result), len(cols))


# ------------------------------------------------------------------- 6. analyze
def analyze(words, lang: str = "Turkish", min_conf: float = 45.0, refine=None, read_cell=None,
            min_pairs: int = 3, size=None, deep: bool = False) -> Result:
    res = Result()
    words = [w for w in words if w.text.strip()]
    all_segs = build_segments(words)
    if not all_segs:
        return res
    res.confidence = round(statistics.fmean(s.conf for s in all_segs), 1)
    res.raw = "\n".join(_join_lines(all_segs))
    segs = drop_noise(all_segs, min_conf)
    if not segs:
        return res
    segs = _split_merged(segs, _centres(segs))
    unit = statistics.median(s.h for s in segs)
    vp, hp = vertical_pairs(segs), horizontal_pairs(segs)
    pairs, res.method = (vp, "vertical") if len(vp) >= len(hp) else (hp, "horizontal")
    pairs = _consistent(pairs)
    if len(pairs) >= min_pairs and 2 * len(pairs) >= 0.5 * len(segs):
        res.kind = "bilingual"
        pairs = _orient(pairs, lang)
        used = {id(s) for p in pairs for s in p}
        bands = _bands(pairs, unit)
        head = _heading(bands)
        if head:
            res.title, res.subtitle = head[0].text, head[1].text
            used.update(id(s) for s in head)
        boxes = []
        if read_cell and res.method == "vertical" and len(bands) >= 2:
            try:
                bands, boxes, res.unread, res.grid = _lattice(bands, read_cell, lang, unit, size, max((x.y1 for x in head), default=0.0) if head else 0.0, deep)
            except Exception:
                pass
        res.rows = [(a.text, b.text) for band in bands for a, b in band]
        if res.rows:
            c1, c2 = _unify_case([r[0] for r in res.rows]), _unify_case([r[1] for r in res.rows])
            res.rows = list(zip(c1, c2))
        res.low = sum(1 for band in bands for a, b in band if (a.conf + b.conf) / 2 < 70)
        res.other = []
    else:
        res.kind = "text"
        res.lines = _paragraphs(segs, unit)
    return res


def rows_top(pairs):
    return min((min(a.y0, b.y0) for a, b in pairs), default=None)


def _join_lines(segs):
    lines = {}
    for s in sorted(segs, key=lambda s: (s.line, s.x0)):
        lines.setdefault(s.line, []).append(s.text)
    return [" ".join(v) for _, v in sorted(lines.items())]


def _paragraphs(segs, unit):
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
    if res.unread:
        out += ["", f"⚠ {res.unread} grid cell(s) could not be read - select that spot with ✂ Select Area."]
    if res.other:
        out += ["", "**Other text:** " + " · ".join(res.other)]
    return "\n".join(out)


def status_line(res: Result, orig_name: str, trans_name: str) -> str:
    if res.kind == "bilingual":
        grid = f" ({res.grid[0]}×{res.grid[1]} grid)" if res.grid else ""
        warn = (f" · ⚠ {res.unread} cell(s) unreadable" if res.unread else "") + (f" · ⚠ {res.low} doubtful" if res.low else "")
        return (f"Bilingual table · {orig_name} → {trans_name} · {len(res.rows)} pairs{grid} · confidence {res.confidence:.0f}%"
                + warn + (" – try Deep OCR" if warn else " · all cells read"))
    if res.kind == "text":
        return f"Clean text · {len(res.lines)} lines · confidence {res.confidence:.0f}%"
    return "No text found"


def score(res: Result):
    return (len(res.rows) - res.unread, -res.low, res.confidence)


# ------------------------------------------------------------------- 7. pair extraction (for CSV)
_BULLET = re.compile(r"^\s*[-*]\s*\**(.+?)\**\s+[—–-]\s+(.+)$")


def extract_pairs(md: str):
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
    out = []
    for line in md.splitlines():
        t = line.strip()
        if t.startswith("|"):
            cells = [c.strip() for c in t.strip("|").split("|")]
            if len(cells) >= 3 and cells[0].isdigit():
                out.append(f"{cells[1]} — {cells[2]}")
            continue
        t = re.sub(r"^#{1,6}\s+", "", line)
        t = re.sub(r"\*+", "", t)
        out.append(re.sub(r"^\s*-\s+", "• ", t))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def full_text(words) -> str:
    lines = {}
    for s in sorted(build_segments(list(words)), key=lambda s: (s.line, s.x0)):
        lines.setdefault(s.line, []).append(s.text)
    return "\n".join("    ".join(v) for _, v in sorted(lines.items()))


def text_notes(md: str, heading: str) -> str:
    body = [ln.strip() for ln in md.splitlines() if ln.strip()]
    return "\n".join([f"## {heading}", *body]) if body else ""


def to_notes(res: Result, md: str, title_vocab: bool = True, vocab_heading: bool = True) -> str:
    pairs = extract_pairs(md)
    if res is not None and res.kind == "bilingual" and pairs:
        out = []
        if res.title:
            out.append(f"# {res.title}")
        if res.subtitle:
            out.append(f"### {res.subtitle}")
        if vocab_heading:
            out.append("## Vocabulary")
        if title_vocab and res.title and res.subtitle:
            out.append(f"- **{res.title}** — {res.subtitle}")
        out += [f"- **{a}** — {b}" for a, b in pairs]
        return "\n".join(out)
    return text_notes(md, "Text") if vocab_heading else "\n".join(x.strip() for x in md.splitlines() if x.strip())


def _norm_pair_text(text: str) -> str:
    """Normalize one side of an OCR/AI pair for deterministic comparison."""
    return re.sub(r"\s+", " ", str(text).strip()).casefold()


def _pair_similarity(a, b) -> float:
    """Return conservative whole-pair similarity, preserving both OCR columns."""
    left = difflib.SequenceMatcher(None, _norm_pair_text(a[0]), _norm_pair_text(b[0])).ratio()
    right = difflib.SequenceMatcher(None, _norm_pair_text(a[1]), _norm_pair_text(b[1])).ratio()
    return min(left, right)


def merge_missing(md: str, rows, extra=()):
    """Append every OCR pair not already represented by the AI markdown.

    Pair presence is evaluated deterministically on BOTH columns. An AI rewrite is
    considered equivalent only when the original and translation each remain at
    least 80% similar. This prevents a source term from being treated as present
    when its translation was silently dropped or replaced. Missing OCR pairs are
    appended once, in stable input order, under ``## More vocabulary (from OCR)``.

    Returns ``(markdown, exact_added_count)``.
    """
    existing = extract_pairs(md)
    candidates = []
    seen = set()
    for pair in list(extra or ()) + list(rows or ()):
        if not pair or len(pair) < 2:
            continue
        normalized = (_norm_pair_text(pair[0]), _norm_pair_text(pair[1]))
        if not normalized[0] and not normalized[1] or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append((str(pair[0]).strip(), str(pair[1]).strip()))

    missing = [pair for pair in candidates
               if not any(_pair_similarity(pair, have) >= 0.80 for have in existing)]
    if not missing:
        return md, 0

    block = "\n".join(f"- **{a}** — {b}" for a, b in missing)
    merged = md.rstrip() + "\n\n## More vocabulary (from OCR)\n" + block
    return merged, len(missing)


def _unify_case(texts):
    low = sum(1 for t in texts if t[:1].islower())
    if low < 0.7 * len(texts):
        return texts
    return [t[0].lower() + t[1:] if len(t) > 2 and t[0] in "ABCDEFGHJKLMNOPQRSTUVWXYZ" and t[1].islower() else t for t in texts]
