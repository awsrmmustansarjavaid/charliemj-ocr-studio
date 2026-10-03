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
