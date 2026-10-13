"""Language discovery without hard-coding the OCR pipeline to Turkish.

The application can use any Tesseract language whose traineddata is installed.
Known friendly names are kept for the original UI; newly discovered language
codes are added automatically so mixed-language OCR does not require a code
change.
"""
from __future__ import annotations

import os

from .config import BASE, LANGS

FRIENDLY = {
    "afr": "Afrikaans", "amh": "Amharic", "ara": "Arabic", "aze": "Azerbaijani",
    "bel": "Belarusian", "ben": "Bengali", "bos": "Bosnian", "bul": "Bulgarian",
    "cat": "Catalan", "ceb": "Cebuano", "ces": "Czech", "chi_sim": "Chinese Simplified",
    "chi_tra": "Chinese Traditional", "dan": "Danish", "deu": "German", "ell": "Greek",
    "eng": "English", "epo": "Esperanto", "est": "Estonian", "eus": "Basque",
    "fas": "Persian", "fin": "Finnish", "fra": "French", "frk": "Frankish",
    "gle": "Irish", "glg": "Galician", "guj": "Gujarati", "heb": "Hebrew",
    "hin": "Hindi", "hrv": "Croatian", "hun": "Hungarian", "ind": "Indonesian",
    "isl": "Icelandic", "ita": "Italian", "jpn": "Japanese", "kan": "Kannada",
    "kat": "Georgian", "kaz": "Kazakh", "khm": "Khmer", "kor": "Korean",
    "lao": "Lao", "lav": "Latvian", "lit": "Lithuanian", "mal": "Malayalam",
    "mar": "Marathi", "mkd": "Macedonian", "mlt": "Maltese", "mon": "Mongolian",
    "msa": "Malay", "mya": "Burmese", "nep": "Nepali", "nld": "Dutch",
    "nor": "Norwegian", "ori": "Odia", "pol": "Polish", "por": "Portuguese",
    "ron": "Romanian", "rus": "Russian", "slk": "Slovak", "slv": "Slovenian",
    "spa": "Spanish", "sqi": "Albanian", "srp": "Serbian", "swa": "Swahili",
    "swe": "Swedish", "tam": "Tamil", "tel": "Telugu", "tha": "Thai",
    "tir": "Tigrinya", "tur": "Turkish", "ukr": "Ukrainian", "urd": "Urdu",
    "uzb": "Uzbek", "vie": "Vietnamese", "yid": "Yiddish",
}


def installed_codes() -> list[str]:
    codes = set()
    tessdata = os.path.join(BASE, "tesseract", "tessdata")
    if os.path.isdir(tessdata):
        for name in os.listdir(tessdata):
            if name.endswith(".traineddata"):
                codes.add(name[:-12])
    try:
        import pytesseract
        codes.update(pytesseract.get_languages(config=""))
    except Exception:
        pass
    return sorted(c for c in codes if c and c not in {"osd", "equ", "frk"})


def choices() -> dict[str, str]:
    """Return display label -> Tesseract code for all currently installed data."""
    out = {name: code.split("+")[0] for name, code in LANGS.items()}
    for code in installed_codes():
        out.setdefault(FRIENDLY.get(code, code), code)
    return dict(sorted(out.items(), key=lambda kv: kv[0].casefold()))


def install() -> dict[str, str]:
    """Extend config.LANGS with every discovered language code."""
    found = installed_codes()
    for code in found:
        LANGS.setdefault(code, code)
    return {code: FRIENDLY.get(code, code) for code in found}
