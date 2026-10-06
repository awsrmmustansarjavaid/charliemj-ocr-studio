"""
make_poster.py - builds a realistic test image: an Instagram-style vocabulary poster
(3 x 5 grid of textured "photos", a bold label with its translation under each photo,
a watermark over the photos, phone status bar on top and a caption at the bottom).

Used by tests/test_ocr_integration.py and for manual experiments. Needs Pillow only.
"""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"
# Ground truth: (Turkish, English) in reading order.
PAIRS = [("gamze", "dimple"), ("çift çene", "double chin"), ("gözenek", "pore"),
         ("çil", "freckle"), ("ben", "mole"), ("güzellik beni", "beauty mark"),
         ("kaz ayağı", "crow's feet"), ("göz altı morluğu", "dark circle"), ("göz altı torbası", "under-eye bag"),
         ("skar", "scar"), ("çatlak", "stretch mark"), ("selülit", "cellulite")]


def font(bold, size):
    try:
        return ImageFont.truetype(FONT % ("-Bold" if bold else ""), size)
    except OSError:                                  # non-Linux: fall back to Arial
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", size)


def make_poster(path, width=1080, seed=3):
    rnd = random.Random(seed)
    cw, ph, lh = (width - 30) // 3, 215, 80           # column width, photo height, label height
    H = 330 + 5 * (ph + lh) + 230
    im = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 20), "7:36", font=font(False, 26), fill="black")
    d.text((width // 2 - 55, 120), "Posts", font=font(True, 40), fill="black")
    d.text((30, 190), "20 hours ago", font=font(False, 22), fill="#777")
    d.text((120, 250), "talkturkish_", font=font(False, 26), fill="black")
    for i, (tr, en) in enumerate(PAIRS):
        c, r = i % 3, i // 3
        x, y = 15 + c * cw, 310 + r * (ph + lh)
        base = (rnd.randint(190, 235), rnd.randint(140, 180), rnd.randint(120, 160))
        photo = Image.blend(Image.new("RGB", (cw - 4, ph), base),
                            Image.effect_noise((cw - 4, ph), 70).convert("RGB"), 0.35).filter(ImageFilter.GaussianBlur(1.2))
        pd = ImageDraw.Draw(photo)
        pd.ellipse((cw // 2 - 40, ph // 2 - 30, cw // 2 + 40, ph // 2 + 30), fill=tuple(int(v * .6) for v in base))
        im.paste(photo, (x, y))
        for text, f, fill, dy in ((tr, font(True, 27), "black", ph + 10), (en, font(False, 20), "#444", ph + 44)):
            w = d.textlength(text, font=f)
            d.text((x + (cw - 4) / 2 - w / 2, y + dy), text, font=f, fill=fill)
    wm = Image.new("RGBA", im.size, (0, 0, 0, 0))     # semi-transparent watermark across the photos
    ImageDraw.Draw(wm).text((250, 640), "TalkTurkish", font=font(True, 90), fill=(255, 255, 255, 110))
    im = Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB")
    d = ImageDraw.Draw(im)
    y = H - 200
    d.text((30, y), "132   1   3   59", font=font(False, 26), fill="black")
    d.text((30, y + 55), "talkturkish_  DESCRIBE SKIN FEATURES IN", font=font(False, 22), fill="black")
    d.text((30, y + 85), "TURKISH!... more", font=font(False, 22), fill="black")
    d.text((30, y + 125), "21 hours ago", font=font(False, 20), fill="#777")
    im.save(path)
    return PAIRS


# ---------------------------------------------------------------------------------------------
# A second fixture: the "Types of Gloves" flashcard - 4 columns, TIGHT labels, a title and a watermark.
# Neighbouring labels almost touch (as on the real card), which used to merge them into one wide
# fragment and lose cells. Ground truth: GLOVES (12 pairs) + the title "ELDİVEN ÇEŞİTLERİ".
GLOVES = [("kışlık eldiven", "winter gloves"), ("muayene eldiveni", "medical gloves"),
          ("temizlik eldiveni", "cleaning gloves"), ("iş eldiveni", "work gloves"),
          ("deri eldiven", "leather gloves"), ("bahçe eldiveni", "gardening gloves"),
          ("fırın eldiveni", "oven mitts"), ("dokunmatik eldiven", "touchscreen gloves"),
          ("parmaksız eldiven", "fingerless gloves"), ("ısıya dayanıklı eldiven", "heat-resistant gloves"),
          ("spor eldiveni", "sports gloves"), ("şık eldiven", "formal gloves")]


def make_gloves(path, width=1080, seed=5, overlap=0, knit=False):
    rnd = random.Random(seed)
    pitch, ph = (width - 20) // 4, 200
    H = 520 + 3 * (ph + 76) + 150
    im = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(im)
    d.text((30, 20), "7:36", font=font(False, 26), fill="black")
    d.text((width // 2 - 55, 110), "Posts", font=font(True, 40), fill="black")
    d.text((120, 240), "talkturkish_", font=font(False, 26), fill="black")
    for txt, f, y in (("ELDİVEN ÇEŞİTLERİ", font(True, 56), 330), ("Types of Gloves", font(False, 38), 400)):
        d.text(((width - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill="black")
    for i, (tr, en) in enumerate(GLOVES):
        c, r = i % 4, i // 4
        x, y = 10 + c * pitch, 480 + r * (ph + 76)
        base = tuple(rnd.randint(40, 230) for _ in range(3))
        photo = Image.blend(Image.new("RGB", (pitch - 30, ph), base), Image.effect_noise((pitch - 30, ph), 60).convert("RGB"), 0.3)
        im.paste(photo, (x + 15, y))
        for text, f, fill, dy in ((tr, font(True, 22), "black", ph + 8), (en, font(False, 17), "#444", ph + 40)):
            w = d.textlength(text, font=f)
            d.text((x + pitch / 2 - w / 2, y + dy), text, font=f, fill=fill)
    wm = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(wm).text((200, 760), "TalkTürkish", font=font(True, 100), fill=(0, 0, 0, 70))
    im = Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((30, H - 130), "45   2   13", font=font(False, 26), fill="black")
    d.text((30, H - 85), "talkturkish_  TYPES OF GLOVES IN TURKISH!... more", font=font(False, 21), fill="black")
    d.text((30, H - 45), "17 hours ago", font=font(False, 20), fill="#777")
    im.save(path)
    return GLOVES


# ---------------------------------------------------------------------------- 4 x 3 glove card
GLOVES = [("kışlık eldiven", "winter gloves"), ("muayene eldiveni", "medical gloves"), ("temizlik eldiveni", "cleaning gloves"),
          ("iş eldiveni", "work gloves"), ("deri eldiven", "leather gloves"), ("bahçe eldiveni", "gardening gloves"),
          ("fırın eldiveni", "oven mitts"), ("dokunmatik eldiven", "touchscreen gloves"), ("parmaksız eldiven", "fingerless gloves"),
          ("ısıya dayanıklı eldiven", "heat-resistant gloves"), ("spor eldiveni", "sports gloves"), ("şık eldiven", "formal gloves")]


def make_gloves(path, width=1080, seed=5, overlap=0, knit=False):
    """A replica of the user's 'Types of Gloves' flashcard: title, 4 x 3 grid, long labels,
    labels close to the page edges, a big watermark, phone header and caption."""
    rnd = random.Random(seed)
    cw, ph, lh = (width - 16) // 4, 205, 62
    H = 400 + 3 * (ph + lh) + 170
    im = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 20), "7:36", font=font(False, 26), fill="black")
    d.text((width // 2 - 55, 110), "Posts", font=font(True, 40), fill="black")
    d.text((120, 230), "talkturkish_", font=font(False, 26), fill="black")
    tf, sf = font(True, 50), font(False, 34)
    d.text(((width - d.textlength("ELDİVEN ÇEŞİTLERİ", font=tf)) / 2, 290), "ELDİVEN ÇEŞİTLERİ", font=tf, fill="black")
    d.text(((width - d.textlength("Types of Gloves", font=sf)) / 2, 350), "Types of Gloves", font=sf, fill="black")
    for i, (tr, en) in enumerate(GLOVES):
        c, r = i % 4, i // 4
        x, y = 8 + c * cw, 410 + r * (ph + lh)
        base = tuple(rnd.randint(60, 220) for _ in range(3))
        photo = Image.blend(Image.new("RGB", (cw - 6, ph + overlap), base), Image.effect_noise((cw - 6, ph + overlap), 80).convert("RGB"), 0.4)
        if knit and c == 0:                       # busy knitted pattern pressing against the label (like the wool glove)
            pd = ImageDraw.Draw(photo)
            for gx in range(0, cw - 6, 6):
                for gy in range(0, ph + overlap, 6):
                    if (gx // 6 + gy // 6) % 2 == 0:
                        pd.rectangle((gx, gy, gx + 5, gy + 5), fill=(30, 30, 30) if rnd.random() < .6 else (240, 240, 240))
        im.paste(photo.filter(ImageFilter.GaussianBlur(0.6)), (x + 3, y))
        for text, f, fill, dy in ((tr, font(True, 19), "black", ph + 8), (en, font(False, 16), "#444", ph + 34)):
            w = d.textlength(text, font=f)
            d.text((x + (cw - 6) / 2 - w / 2 + 3, y + dy), text, font=f, fill=fill)
    wm = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(wm).text((200, 760), "TalkTürkish", font=font(True, 110), fill=(60, 60, 60, 90))
    im = Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((30, H - 150), "45   2   2   13", font=font(False, 26), fill="black")
    d.text((30, H - 100), "talkturkish_  TYPES OF GLOVES IN TURKISH!... more", font=font(False, 22), fill="black")
    d.text((30, H - 60), "17 hours ago", font=font(False, 20), fill="#777")
    im.save(path)
    return GLOVES


GLOVES = [("kışlık eldiven", "winter gloves"), ("muayene eldiveni", "medical gloves"), ("temizlik eldiveni", "cleaning gloves"),
          ("iş eldiveni", "work gloves"), ("deri eldiven", "leather gloves"), ("bahçe eldiveni", "gardening gloves"),
          ("fırın eldiveni", "oven mitts"), ("dokunmatik eldiven", "touchscreen gloves"), ("parmaksız eldiven", "fingerless gloves"),
          ("ısıya dayanıklı eldiven", "heat-resistant gloves"), ("spor eldiveni", "sports gloves"), ("şık eldiven", "formal gloves")]


def make_gloves(path, width=1080, seed=5):
    """A harder replica of a real 4 x 3 flashcard: labels start at the very left edge, the English text is small and
    light grey, long labels almost touch their neighbours, a huge watermark crosses the photos of row 2."""
    rnd = random.Random(seed)
    cw, ph = width // 4, 250
    H = 520 + 3 * (ph + 95) + 200
    im = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 20), "7:36", font=font(False, 26), fill="black")
    d.text((width // 2 - 55, 110), "Posts", font=font(True, 40), fill="black")
    d.text((120, 240), "talkturkish_", font=font(False, 26), fill="black")
    d.text((width // 2 - 215, 320), "ELDİVEN ÇEŞİTLERİ", font=font(True, 52), fill="black")
    d.text((width // 2 - 135, 385), "Types of Gloves", font=font(False, 34), fill="black")
    for i, (tr, en) in enumerate(GLOVES):
        c, r = i % 4, i // 4
        x, y = 4 + c * cw, 450 + r * (ph + 95)
        base = tuple(rnd.randint(40, 230) for _ in range(3))
        photo = Image.blend(Image.new("RGB", (cw - 8, ph), base), Image.effect_noise((cw - 8, ph), 90).convert("RGB"), 0.4)
        im.paste(photo.filter(ImageFilter.GaussianBlur(1.0)), (x, y))
        for text, f, fill, dy in ((tr, font(True, 24), "#111111", ph + 8), (en, font(False, 17), "#8a8a8a", ph + 40)):
            w = d.textlength(text, font=f)
            d.text((x + (cw - 8) / 2 - w / 2, y + dy), text, font=f, fill=fill)
    wm = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(wm).text((120, 450 + ph + 95 + 40), "TalkTürkish", font=font(True, 150), fill=(120, 120, 120, 120))
    Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB").save(path)
    return GLOVES


# --------------------------------------------------------------------------- the glove flashcard
GLOVES = [("kışlık eldiven", "winter gloves"), ("muayene eldiveni", "medical gloves"), ("temizlik eldiveni", "cleaning gloves"),
          ("iş eldiveni", "work gloves"), ("deri eldiven", "leather gloves"), ("bahçe eldiveni", "gardening gloves"),
          ("fırın eldiveni", "oven mitts"), ("dokunmatik eldiven", "touchscreen gloves"), ("parmaksız eldiven", "fingerless gloves"),
          ("ısıya dayanıklı eldiven", "heat-resistant gloves"), ("spor eldiveni", "sports gloves"), ("şık eldiven", "formal gloves")]


NARROW = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed%s.ttf"


def narrow(bold, size):
    """A condensed sans font (long labels stay tall and readable); falls back to the normal font."""
    try:
        return ImageFont.truetype(NARROW % ("-Bold" if bold else ""), size)
    except OSError:
        return font(bold, size)


def make_card(path, width=1080, tight=0.95):
    """A 4 x 3 flashcard like an Instagram vocabulary post: big title + subtitle, a photo above every label,
    labels that almost touch their neighbours (`tight` = widest label / column width) and a watermark.
    Returns the 13 ground-truth phrases: the title pair first, then the 12 labels."""
    rnd = random.Random(7)
    pitch = (width - 30) / 4
    size = 40
    while narrow(True, size).getlength("ısıya dayanıklı eldiven") > tight * pitch:     # fit the longest label
        size -= 1
    f_tr, f_en = narrow(True, size), narrow(False, max(10, int(size * 0.82)))
    ph, lh, top = 200, 74, 420
    H = top + 3 * (ph + lh) + 240
    im = Image.new("RGB", (width, H), "white")
    d = ImageDraw.Draw(im)
    d.text((40, 20), "7:36", font=font(False, 26), fill="black")
    d.text((width // 2 - 55, 110), "Posts", font=font(True, 40), fill="black")
    d.text((30, 190), "16 hours ago", font=font(False, 22), fill="#777")
    d.text((120, 240), "talkturkish_", font=font(False, 26), fill="black")
    for text, f, y in (("ELDİVEN ÇEŞİTLERİ", font(True, 50), 305), ("Types of Gloves", font(False, 34), 365)):
        d.text(((width - d.textlength(text, font=f)) / 2, y), text, font=f, fill="black")
    for i, (tr, en) in enumerate(GLOVES):
        c, r = i % 4, i // 4
        x, y = 15 + c * pitch, top + r * (ph + lh)
        for _ in range(7):                                          # a "glove": dark/bright blobs on a white background
            bx, by = x + rnd.randint(30, int(pitch) - 90), y + rnd.randint(5, ph - 100)
            col = tuple(rnd.randint(20, 220) for _ in range(3))
            d.ellipse((bx, by, bx + rnd.randint(30, 70), min(by + rnd.randint(50, 130), y + ph - 6)), fill=col)   # stays above the label
        for text, ff, dy, fill in ((tr, f_tr, ph + 8, "black"), (en, f_en, ph + 8 + size + 6, "#444")):
            d.text((x + pitch / 2 - d.textlength(text, font=ff) / 2, y + dy), text, font=ff, fill=fill)
    wm = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(wm).text((120, top + ph + lh + 40), "TalkTürkish", font=font(True, 130), fill=(120, 120, 120, 90))
    im = Image.alpha_composite(im.convert("RGBA"), wm).convert("RGB")
    d = ImageDraw.Draw(im)
    d.text((30, H - 190), "45   2   13", font=font(False, 26), fill="black")
    d.text((30, H - 140), "talkturkish_  TYPES OF GLOVES IN TURKISH!", font=font(False, 22), fill="black")
    d.text((30, H - 60), "17 hours ago", font=font(False, 20), fill="#777")
    im.save(path)
    return [("ELDİVEN ÇEŞİTLERİ", "Types of Gloves")] + GLOVES
