"""
ocr_engine.py - local, offline OCR using the bundled Tesseract engine.

Unlike a plain "image to string" call, read_words() returns every word WITH its
bounding box and confidence. layout.py uses those coordinates to rebuild the
structure of the picture (columns, label/translation pairs, titles).

make_refiner() adds a second pass: small labels are re-read one by one with
single-language models (e.g. Turkish only / English only), which is often
more accurate than the mixed "tur+eng" model on short phrases.

v1.2 additions
    read_raw()        RAW mode: sparse (--psm 11) + automatic (--psm 3) passes combined, nothing dropped
    make_cell_reader  re-reads one empty grid cell as a two-line block (used to fill missing cells)
    make_refiner      now refuses readings that lost letters or changed the word (a photo edge
                      could cut "güzellik beni" down to "bea")
"""
import os

import pytesseract
from PIL import Image, ImageOps, ImageStat

from .config import BASE, LANGS, cfg
from .layout import Word

# Use the Tesseract folder shipped next to the app, if present (portable build).
_T = os.path.join(BASE, "tesseract")
if os.path.exists(os.path.join(_T, "tesseract.exe")):
    pytesseract.pytesseract.tesseract_cmd = os.path.join(_T, "tesseract.exe")
    os.environ["TESSDATA_PREFIX"] = os.path.join(_T, "tessdata")


def prepare(img: Image.Image, scale: float = None) -> Image.Image:
    """Make an image easier to read: grayscale, fix dark themes, boost contrast, upscale small text."""
    g = ImageOps.grayscale(img)
    if ImageStat.Stat(g).mean[0] < 110:        # light text on dark background -> invert
        g = ImageOps.invert(g)
    g = ImageOps.autocontrast(g)
    k = scale or (2 if g.width < 1600 else 1)   # phone screenshots have tiny text: enlarge them
    if k != 1:
        g = g.resize((int(g.width * k), int(g.height * k)), Image.LANCZOS)
    return g


def read_text(img: Image.Image, code: str = None) -> str:
    """Raw mode: plain OCR text (Tesseract's own layout analysis)."""
    return pytesseract.image_to_string(prepare(img), lang=code or LANGS[cfg["lang"]]).strip()


def read_words(img: Image.Image, code: str = None, scale: float = None):
    """Smart mode: returns (words with boxes, prepared image).

    Uses sparse-text mode (--psm 11), best for cards and posters. The coordinates
    refer to the PREPARED image, which is also returned for the refiner.
    """
    g = prepare(img, scale)
    d = pytesseract.image_to_data(g, lang=code or LANGS[cfg["lang"]], config="--psm 11",
                                  output_type=pytesseract.Output.DICT)
    words = []
    for i, t in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except ValueError:
            continue
        if t.strip() and conf >= 0:
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            words.append(Word(t.strip(), x, y, x + w, y + h, conf))
    return words, g


def make_refiner(prepped: Image.Image, code_a: str, code_b: str):
    """Return refine(seg, role) -> str | None  (used by layout.analyze).

    role "orig"  = a cell in the language being learned  -> read with code_a (e.g. 'tur')
    role "trans" = a cell in the translation language    -> read with code_b (e.g. 'eng')

    The crop is re-read as ONE line (--psm 7) with that single-language model, which is
    much better for letters such as ş ı ğ ç. The new text is returned only when it is
    about as confident as the first reading; otherwise None (keep the original).
    """
    def refine(seg, role):
        code = code_a if role == "orig" else code_b
        pad = int(seg.h * 0.35)
        padx = int(getattr(seg, "padx", 0) or pad)          # wider margin: letters lost at the edges can come back
        crop = prepped.crop((max(0, int(seg.x0) - padx), max(0, int(seg.y0) - pad),
                             min(prepped.width, int(seg.x1) + padx), min(prepped.height, int(seg.y1) + pad)))
        if crop.height < 48:                                   # Tesseract likes ~40 px letters
            k = 48 / crop.height
            crop = crop.resize((max(1, int(crop.width * k)), 48), Image.LANCZOS)
        crop = ImageOps.expand(crop, border=10, fill=255)
        d = pytesseract.image_to_data(crop, lang=code, config="--psm 7", output_type=pytesseract.Output.DICT)
        got = []
        for t, cf in zip(d["text"], d["conf"]):
            try:
                if t.strip() and float(cf) >= 0:
                    got.append((t.strip(), float(cf)))
            except ValueError:
                pass
        if not got:
            return None
        conf = sum(c for _, c in got) / len(got)
        text = " ".join(t for t, _ in got)
        if conf < 50 or conf < seg.conf - 8:
            return None
        old = seg.text.lower()
        if len(text) < 0.85 * len(old) or difflib.SequenceMatcher(None, old, text.lower()).ratio() < 0.6:
            return None          # truncated or a different word (e.g. cut by a photo edge): keep the first reading
        return text

    return refine


# ---------------------------------------------------------------------------- v1.2 additions
import difflib
import unicodedata

from . import layout


def _words(g, code, psm):
    """Words with boxes from one Tesseract pass (page-segmentation mode psm) on a prepared image."""
    d = pytesseract.image_to_data(g, lang=code, config=f"--psm {psm}", output_type=pytesseract.Output.DICT)
    out = []
    for i, t in enumerate(d["text"]):
        try:
            conf = float(d["conf"][i])
        except ValueError:
            continue
        if t.strip() and conf >= 0:
            x, y, w, h = d["left"][i], d["top"][i], d["width"][i], d["height"][i]
            out.append(Word(t.strip(), x, y, x + w, y + h, conf))
    return out


def _fold(t: str) -> str:
    """Lower-case and remove accents (ç ğ ı ö ş ü ...) - used to compare two readings of the same word."""
    t = t.lower().replace("ı", "i").replace("İ", "i")
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def read_raw(img: Image.Image, code: str = None) -> str:
    """RAW mode - the COMPLETE text of the picture, nothing filtered out.

    Three Tesseract passes are combined:
      * sparse mode (--psm 11)            finds scattered text such as card labels
      * automatic page analysis (--psm 3) any word found by only one of the two passes is kept
      * learning-language model only      corrects accents: a word that differs from the mixed model's reading
                                          ONLY by accents (kislik -> kışlık) takes the better-accented spelling
    """
    code = code or LANGS[cfg["lang"]]
    g = prepare(img)
    a, b = _words(g, code, 11), _words(g, code, 3)
    first = code.split("+")[0]
    if first != "eng":                                           # accent fix with the single-language model
        c = _words(g, first, 11)
        for w in a:
            cx, cy = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
            for r in c:
                if r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 and r.text != w.text and _fold(r.text) == _fold(w.text) \
                        and r.conf >= w.conf - 5:
                    w.text = r.text
                    break

    def seen(w):
        cx, cy = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
        return any(r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 for r in a)
    return layout.full_text(a + [w for w in b if not seen(w)])


def _snap(img: Image.Image, x: float, y0: float, y1: float, w: float) -> float:
    """Move a cell boundary into the WIDEST empty gap near x: the space between two neighbouring labels.

    Window: +-0.2 x the cell width. The gap between two cards is wider than the space between two words of
    one label, so the widest white run is the real border (ties go to the run nearest to x). Even when the
    estimated grid is a little off, every word still lands in the cell it really belongs to.
    """
    lo, hi = max(0, int(x - 0.2 * w)), min(img.width, int(x + 0.2 * w))
    if hi - lo < 6 or y1 - y0 < 4:
        return x
    prof = list(img.convert("L").crop((lo, int(y0), hi, int(y1))).resize((hi - lo, 1), Image.BOX).tobytes())     # mean grey per column
    white = [v >= 245 for v in prof]                                       # an (almost) empty pixel column
    runs, start = [], None
    for i, wv in enumerate(white + [False]):
        if wv and start is None:
            start = i
        elif not wv and start is not None:
            runs.append((start, i - 1))
            start = None
    if not runs:                                                           # no empty column: take the lightest one
        return lo + max(range(len(prof)), key=lambda i: (prof[i], -abs(lo + i - x)))
    widest = max(r[1] - r[0] for r in runs)
    best = min((r for r in runs if r[1] - r[0] >= widest - 1), key=lambda r: abs(lo + (r[0] + r[1]) / 2 - x))
    return lo + (best[0] + best[1]) / 2


def make_cell_reader(prepped: Image.Image, code: str, code_a: str = None, code_b: str = None):
    """Return read_cell(box) -> [(text, confidence), ...]  (one entry per text line, top to bottom).

    Used for card grids: every cell (picture label + translation) is read again on its own.
    role="orig" / "trans" reads with a single-language model (code_a / code_b) - used by Deep OCR to fix
    letters such as ş ı ğ ç that the mixed model sometimes confuses.
    The crop is deliberately WIDER than the cell (labels often overflow into the gap between two
    cards) and is read in sparse mode (--psm 11); then only the words whose CENTRE lies inside the cell
    are kept. So no letter is ever cut off, and text of the neighbouring card never leaks in.
    """
    def read_cell(box, snap=True, role=None):
        x0, y0, x1, y1 = box
        w = x1 - x0
        if snap:                                             # use the real gaps between labels as cell borders
            x0, x1 = _snap(prepped, x0, y0, y1, w), _snap(prepped, x1, y0, y1, w)
        cx0, cx1 = max(0, int(x0 - 0.35 * w)), min(prepped.width, int(x1 + 0.35 * w))
        cy0, cy1 = max(0, int(y0)), min(prepped.height, int(y1))
        if cx1 - cx0 < 8 or cy1 - cy0 < 8:
            return []
        crop = prepped.crop((cx0, cy0, cx1, cy1))
        k = max(1.0, 150 / crop.height)                      # make two text lines about 70 px tall each
        if k > 1:
            crop = crop.resize((int(crop.width * k), int(crop.height * k)), Image.LANCZOS)
        pad = 14
        crop = ImageOps.expand(crop, border=pad, fill=255)
        lang = (code_a if role == "orig" else code_b if role == "trans" else None) or code   # single-language model for Deep OCR
        d = pytesseract.image_to_data(crop, lang=lang, config="--psm 11", output_type=pytesseract.Output.DICT)
        found = []                                           # (centre y, left, text, conf, height)
        for i, t in enumerate(d["text"]):
            try:
                c = float(d["conf"][i])
            except ValueError:
                continue
            if not t.strip() or c < 0:
                continue
            cx = cx0 + (d["left"][i] + d["width"][i] / 2 - pad) / k           # back to prepared-image pixels
            if x0 <= cx <= x1:
                found.append((d["top"][i] + d["height"][i] / 2, d["left"][i], t.strip(), c, d["height"][i]))
        found.sort()
        lines = []
        for f in found:                                      # words on the same y belong to one line
            if lines and abs(f[0] - lines[-1][-1][0]) <= 0.6 * max(f[4], lines[-1][-1][4]):
                lines[-1].append(f)
            else:
                lines.append([f])
        return [(" ".join(x[2] for x in sorted(ln, key=lambda x: x[1])), sum(x[3] for x in ln) / len(ln)) for ln in lines]
    return read_cell
