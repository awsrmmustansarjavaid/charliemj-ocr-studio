
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
        if refine:
            for a, b in (p for band in bands for p in band):
                for seg, role in ((a, "orig"), (b, "trans")):
                    try:
                        seg.text = clean_text(refine(seg, role) or seg.text)
                    except Exception:
                        pass
        boxes = []
        if read_cell and res.method == "vertical" and len(bands) >= 2:
            try:
                bands, boxes, res.unread, res.grid = _lattice(bands, read_cell, lang, unit, size, max((x.y1 for x in head), default=0.0) if head else 0.0, deep)
            except Exception:
                pass
        if head and read_cell:
            try:
                bx = (min(s.x0 for s in head) - 4, min(s.y0 for s in head) - 0.3 * head[0].h,
                      max(s.x1 for s in head) + 4, max(s.y1 for s in head) + 0.3 * head[0].h)
                got = _pick_lines(read_cell(bx, False))
                if len(got) == 2 and all(len(clean_text(t)) >= 0.8 * len(o) for (t, _), o in zip(got, (res.title, res.subtitle))):
                    res.title, res.subtitle = clean_text(got[0][0]), clean_text(got[1][0])
            except Exception:
                pass
        res.rows = [(a.text, b.text) for band in bands for a, b in band]
        if res.rows:
            c1, c2 = _unify_case([r[0] for r in res.rows]), _unify_case([r[1] for r in res.rows])
            res.rows = list(zip(c1, c2))
        res.low = sum(1 for band in bands for a, b in band if (a.conf + b.conf) / 2 < 70)

        def in_box(s):
            return any(bx[0] <= (s.x0 + s.x1) / 2 <= bx[2] and bx[1] <= s.cy <= bx[3] for bx in boxes)
        left = [s for s in sorted(segs, key=lambda s: (s.cy, s.x0)) if id(s) not in used and not in_box(s)]
        top = rows_top([p for band in bands for p in band])
        if not res.title and top is not None:
            big = [s for s in left if s.y1 <= top + 0.5 * unit and s.conf >= 70
                   and (s.h >= 1.6 * unit or (s.h >= 1.25 * unit and top - s.y1 <= 3 * unit))]
            if big:
                h = max(big, key=lambda s: s.h)
                res.title = h.text
                left.remove(h)
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
    if res.unread:
        out += ["", f"⚠ {res.unread} grid cell(s) could not be read - select that spot with ✂ Select Area."]
    if res.other:
        out += ["", "**Other text:** " + " · ".join(res.other)]
    return "\n".join(out)


def status_line(res: Result, orig_name: str, trans_name: str) -> str:
    """One-line summary shown in the status bar after OCR, including the coverage check."""
    if res.kind == "bilingual":
        grid = f" ({res.grid[0]}×{res.grid[1]} grid)" if res.grid else ""
        warn = (f" · ⚠ {res.unread} cell(s) unreadable" if res.unread else "") + (f" · ⚠ {res.low} doubtful" if res.low else "")
        return (f"Bilingual table · {orig_name} → {trans_name} · {len(res.rows)} pairs{grid} · confidence {res.confidence:.0f}%"
                + warn + (" – try Deep OCR" if warn else " · all cells read"))
    if res.kind == "text":
        return f"Clean text · {len(res.lines)} lines · confidence {res.confidence:.0f}%"
    return "No text found"


def score(res: Result):
    """How complete a Smart result is (higher is better) - used to choose between two OCR passes."""
    return (len(res.rows) - res.unread, -res.low, res.confidence)


# ------------------------------------------------------------------- 7. pair extraction (for CSV)
_BULLET = re.compile(r"^\s*[-*]\s*\**(.+?)\**\s+[—–-]\s+(.+)$")


def extract_pairs(md: str):
    """Read (original, translation) pairs back out of Markdown text."""
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
            continue
        t = re.sub(r"^#{1,6}\s+", "", line)
        t = re.sub(r"\*+", "", t)
        out.append(re.sub(r"^\s*-\s+", "• ", t))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def full_text(words) -> str:
    """RAW mode: every word, nothing removed or reordered by guesswork."""
    lines = {}
    for s in sorted(build_segments(list(words)), key=lambda s: (s.line, s.x0)):
        lines.setdefault(s.line, []).append(s.text)
    return "\n".join("    ".join(v) for _, v in sorted(lines.items()))


def text_notes(md: str, heading: str) -> str:
    """Notes Markdown for plain text."""
    body = [ln.strip() for ln in md.splitlines() if ln.strip()]
    return "\n".join([f"## {heading}", *body]) if body else ""


def to_notes(res: Result, md: str, title_vocab: bool = True, vocab_heading: bool = True) -> str:
    """Study-notes Markdown for the text editor."""
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


def merge_missing(md: str, rows, extra=()):
    """Safety net for AI Smart: add OCR pairs that AI notes do not contain."""
    have = [a.lower() for a, _ in extract_pairs(md)]
    miss = [(a, b) for a, b in list(extra) + list(rows)
            if not any(difflib.SequenceMatcher(None, a.lower(), h).ratio() >= 0.8 for h in have)]
    if not miss:
        return md, 0
    return md.rstrip() + "\n\n## More vocabulary (from OCR)\n" + "\n".join(f"- **{a}** — {b}" for a, b in miss), len(miss)


def _unify_case(texts):
    """If almost every text of a column starts lower-case, lower-case the odd capitalized item."""
    low = sum(1 for t in texts if t[:1].islower())
    if low < 0.7 * len(texts):
        return texts
    return [t[0].lower() + t[1:] if len(t) > 2 and t[0] in "ABCDEFGHJKLMNOPQRSTUVWXYZ" and t[1].islower() else t for t in texts]


# v2.0 coverage guard: install only after every legacy layout function exists.
# The guard is optional and self-contained; it never changes the RAW OCR path.
try:
    from app.v2_truth import install as _install_v2_truth
    _install_v2_truth()
except Exception:
    pass
