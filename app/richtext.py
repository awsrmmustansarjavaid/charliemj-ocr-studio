"""
richtext.py - the document model behind the text editor (pure Python, no Tk).

A document is a list of Blocks (one block = one paragraph / line). A block has a
style (normal, title, h1, h2, h3), an alignment and a list of Runs (pieces of text
with their own formatting). Keeping the model separate from the widget makes it easy
to test and lets one model feed every exporter:

    Markdown --md_to_blocks--> [Block] --blocks_to_md / _text / _html / write_docx--> files

Bullet and numbered lists are ordinary text prefixes ("• " and "1. "), so they survive
every export format.
"""
import html
import re
import zipfile
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

BULLET = "• "
LEVELS = ["title", "h1", "h2", "h3"]                      # heading levels, biggest first
STYLE_SIZE = {"normal": 13, "title": 26, "h1": 21, "h2": 17, "h3": 14}   # default point sizes
STYLE_BOLD = {"title", "h1", "h2", "h3"}
PREFIX = {"title": "# ", "h1": "## ", "h2": "### ", "h3": "#### "}        # Markdown export


@dataclass
class Run:
    """A piece of text with one formatting."""
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    size: int = None          # explicit point size (None = the paragraph style's size)
    color: str = None         # "#rrggbb" text colour
    bg: str = None            # "#rrggbb" highlight


@dataclass
class Block:
    """One paragraph."""
    style: str = "normal"
    align: str = "left"       # left | center | right
    runs: list = field(default_factory=list)
    hr: bool = False          # a horizontal separator line

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)

    @property
    def is_bullet(self) -> bool:
        return self.text.startswith(BULLET)


# ------------------------------------------------------------------ Markdown -> blocks
_INLINE = re.compile(r"(\*\*.+?\*\*|\*[^*\n]+?\*)")
_SEP = re.compile(r"^\|?[\s:\-|]+\|?$")                   # a table separator row  |---|---|


def _inline(text, **base):
    """Split '**bold** and *italic*' into runs."""
    runs = []
    for part in _INLINE.split(text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**") and len(part) > 4:
            runs.append(Run(part[2:-2], bold=True, **base))
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            runs.append(Run(part[1:-1], italic=True, **base))
        else:
            runs.append(Run(part, **base))
    return runs


def md_to_blocks(md: str, top: str = "h1"):
    """Markdown -> blocks. '#' becomes style `top` (h1 by default), '##' the next level, ...

    Tables become bullets ('• first — second') so vocabulary tables turn into bullet lists.
    """
    start, out, lines = LEVELS.index(top), [], md.splitlines()
    for k, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if re.fullmatch(r"-{3,}|_{3,}|\*{3,}", s):
            out.append(Block(hr=True))
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", s)
        if m:
            out.append(Block(LEVELS[min(len(m.group(1)) - 1 + start, 3)], runs=_inline(m.group(2))))
            continue
        if s.startswith("|"):
            nxt = lines[k + 1].strip() if k + 1 < len(lines) else ""
            if _SEP.match(s) or (nxt.startswith("|") and _SEP.match(nxt)):
                continue                                   # separator row / header row
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells[0].isdigit() and len(cells) >= 3:
                cells = cells[1:]
            if len(cells) >= 2:
                out.append(Block(runs=[Run(BULLET), Run(cells[0], bold=True), Run(" — " + " — ".join(cells[1:]))]))
                continue
        m = re.match(r"^[-*•]\s+(.*)", s)
        if m:
            out.append(Block(runs=[Run(BULLET)] + _inline(m.group(1))))
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)", s)
        if m:
            out.append(Block(runs=[Run(f"{m.group(1)}. ")] + _inline(m.group(2))))
            continue
        out.append(Block(runs=_inline(s)))
    return out


# ------------------------------------------------------------------ blocks -> text formats
def _wrap(text, marker):
    core = text.strip()
    if not core:
        return text
    lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
    return f"{lead}{marker}{core}{marker}{trail}"


def blocks_to_md(blocks) -> str:
    """Blocks -> Markdown (title '#', h1 '##', h2 '###', h3 '####'; bullets '- ')."""
    out = []
    for b in blocks:
        if b.hr:
            out.append("---")
            continue
        text = ""
        for r in b.runs:
            t = r.text
            if b.style == "normal":
                if r.bold and r.italic:
                    t = _wrap(t, "***")
                elif r.bold:
                    t = _wrap(t, "**")
                elif r.italic:
                    t = _wrap(t, "*")
            text += t
        if text.startswith(BULLET):
            text = "- " + text[len(BULLET):]
        out.append(PREFIX.get(b.style, "") + text)
    return "\n".join(out)


def blocks_to_text(blocks) -> str:
    """Blocks -> plain text (bullets and numbers stay; separators become a line)."""
    return "\n".join("──────────" if b.hr else b.text for b in blocks)


def blocks_pairs(blocks):
    """Vocabulary bullets '• word — meaning' -> [(image number, word, meaning)]."""
    img, out = 0, []
    for b in blocks:
        t = b.text
        m = re.match(r"^Image (\d+)\s*$", t)
        if b.style == "title" and m:
            img = int(m.group(1))
        elif b.is_bullet and " — " in t:
            a, _, c = t[len(BULLET):].partition(" — ")
            out.append((img, a.strip(), c.strip()))
    return out


def _eff(block, run):
    """Effective (size, bold, italic) of a run, taking the paragraph style into account."""
    size = run.size or STYLE_SIZE.get(block.style, 13)
    return size, run.bold or block.style in STYLE_BOLD, run.italic or block.style == "h3"


def blocks_to_html(blocks, title="Study notes") -> str:
    """Blocks -> a self-contained HTML page (bullets grouped into <ul>)."""
    tag = {"title": "h1", "h1": "h2", "h2": "h3", "h3": "h4"}
    body, in_list = [], False
    for b in blocks:
        spans = ""
        for r in b.runs:
            size, bold, italic = _eff(b, r)
            css = [f"font-size:{size}pt"] if r.size else []
            css += (["font-weight:bold"] if r.bold else []) + (["font-style:italic"] if r.italic else [])
            css += (["text-decoration:underline"] if r.underline else []) + (["text-decoration:line-through"] if r.strike else [])
            css += ([f"color:{r.color}"] if r.color else []) + ([f"background:{r.bg}"] if r.bg else [])
            txt = html.escape(r.text[len(BULLET):] if b.is_bullet and r is b.runs[0] and r.text == BULLET else r.text)
            spans += f'<span style="{";".join(css)}">{txt}</span>' if css else txt
        if b.is_bullet and not b.hr:
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{spans}</li>")
            continue
        if in_list:
            body.append("</ul>")
            in_list = False
        al = f' style="text-align:{b.align}"' if b.align != "left" else ""
        if b.hr:
            body.append("<hr>")
        elif b.style in tag:
            body.append(f"<{tag[b.style]}{al}>{spans}</{tag[b.style]}>")
        else:
            body.append(f"<p{al}>{spans or '&nbsp;'}</p>")
    if in_list:
        body.append("</ul>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>%s</title><style>body{font-family:Segoe UI,Arial,"
            "sans-serif;max-width:820px;margin:2em auto;line-height:1.5}h1{margin-top:1.4em}</style></head><body>\n%s\n"
            "</body></html>" % (html.escape(title), "\n".join(body)))


def write_docx(path, blocks) -> None:
    """Write a minimal but valid Word document (.docx) - no extra libraries needed."""
    paras = []
    for b in blocks:
        if b.hr:
            paras.append('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="999999"/></w:pBdr></w:pPr></w:p>')
            continue
        runs = ""
        for r in b.runs:
            size, bold, italic = _eff(b, r)
            pr = '<w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI" w:cs="Segoe UI"/>'
            pr += ("<w:b/>" if bold else "") + ("<w:i/>" if italic else "") + ("<w:strike/>" if r.strike else "")
            pr += '<w:u w:val="single"/>' if r.underline else ""
            pr += f'<w:color w:val="{r.color.lstrip("#")}"/>' if r.color else ""
            pr += f'<w:sz w:val="{int(size * 2)}"/>'
            pr += f'<w:shd w:val="clear" w:color="auto" w:fill="{r.bg.lstrip("#")}"/>' if r.bg else ""
            runs += f'<w:r><w:rPr>{pr}</w:rPr><w:t xml:space="preserve">{escape(r.text)}</w:t></w:r>'
        jc = f'<w:pPr><w:jc w:val="{b.align}"/></w:pPr>' if b.align != "left" else ""
        paras.append(f"<w:p>{jc}{runs}</w:p>")
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>' + "".join(paras) + "<w:sectPr/></w:body></w:document>")
    types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/'
             'content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType='
             '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/'
            'package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            'relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", doc)
