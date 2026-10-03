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


def prepare(img: Image.Image) -> Image.Image:
    """Make an image easier to read: grayscale, fix dark themes, boost contrast, upscale small text."""
    g = ImageOps.grayscale(img)
    if ImageStat.Stat(g).mean[0] < 110:        # light text on dark background -> invert
        g = ImageOps.invert(g)
    g = ImageOps.autocontrast(g)
    if g.width < 1600:                          # phone screenshots have tiny text
        g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
    return g


def read_text(img: Image.Image, code: str = None) -> str:
    """Raw mode: plain OCR text (Tesseract's own layout analysis)."""
    return pytesseract.image_to_string(prepare(img), lang=code or LANGS[cfg["lang"]]).strip()


def read_words(img: Image.Image, code: str = None):
    """Smart mode: returns (words with boxes, prepared image).

    Uses sparse-text mode (--psm 11), best for cards and posters. The coordinates
    refer to the PREPARED image, which is also returned for the refiner.
    """
    g = prepare(img)
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
        crop = prepped.crop((max(0, int(seg.x0) - pad), max(0, int(seg.y0) - pad),
                             min(prepped.width, int(seg.x1) + pad), min(prepped.height, int(seg.y1) + pad)))
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


def read_raw(img: Image.Image, code: str = None) -> str:
    """RAW mode - the COMPLETE text of the picture, nothing filtered out.

    Two Tesseract passes are combined: sparse mode (--psm 11, finds scattered text such as
    card labels) plus automatic page analysis (--psm 3). Any word found by only one pass is kept.
    """
    code = code or LANGS[cfg["lang"]]
    g = prepare(img)
    a, b = _words(g, code, 11), _words(g, code, 3)

    def seen(w):
        cx, cy = (w.x0 + w.x1) / 2, (w.y0 + w.y1) / 2
        return any(r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1 for r in a)
    return layout.full_text(a + [w for w in b if not seen(w)])


def make_cell_reader(prepped: Image.Image, code: str):
    """Return read_cell(box) -> [(text, confidence), ...] (one entry per text line).

    Used to recover table cells the first pass missed: the box is cropped from the
    prepared image, enlarged, and read as a small text block (--psm 6).
    """
    def read_cell(box):
        x0, y0, x1, y1 = (int(max(0, v)) for v in box)
        crop = prepped.crop((x0, y0, min(prepped.width, x1), min(prepped.height, y1)))
        if crop.width < 8 or crop.height < 8:
            return []
        k = max(1.0, 90 / crop.height)                       # make the two text lines ~45 px tall each
        crop = ImageOps.expand(crop.resize((int(crop.width * k), int(crop.height * k)), Image.LANCZOS), border=12, fill=255)
        d = pytesseract.image_to_data(crop, lang=code, config="--psm 6", output_type=pytesseract.Output.DICT)
        rows = {}
        for i, t in enumerate(d["text"]):
            try:
                c = float(d["conf"][i])
            except ValueError:
                continue
            if t.strip() and c >= 0:
                rows.setdefault((d["block_num"][i], d["par_num"][i], d["line_num"][i]), []).append((t.strip(), c))
        return [(" ".join(t for t, _ in v), sum(c for _, c in v) / len(v)) for _, v in sorted(rows.items())]
    return read_cell
