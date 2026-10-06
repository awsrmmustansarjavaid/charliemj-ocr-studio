"""
config.py - paths, constants and the settings file (config.json).

Everything the app saves lives NEXT TO the .exe (BASE folder), which is what
makes it portable: copy the folder to a USB drive and your settings go with it.
No registry entries are written and no admin rights are needed.
"""
import json
import os
import sys

# Folder containing the .exe (PyInstaller) or the project root (running from source).
BASE = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG_PATH = os.path.join(BASE, "config.json")

# Defaults - used for any key missing from config.json.
DEFAULTS = {
    "batch_limit": 20,                      # max images in the queue
    "lang": "Turkish",                      # language being learned (drives OCR + table headers)
    "native": "English",                    # the "translation" column / AI answers
    "level": "Beginner",                    # learner level for AI vocabulary
    "mode": "Smart",                        # "Smart" (structured) or "Raw" (plain OCR)
    "min_conf": 45,                         # drop OCR fragments below this confidence (0-100)
    "ollama_url": "http://127.0.0.1:11434", # local AI server (Ollama) - localhost only
    "model": "gemma3:4b",                   # local model name (must be pulled in Ollama)
    "theme": "dark",
    "accuracy": "Balanced",                 # Fast | Balanced | Deep (Deep re-reads every cell and retries doubtful images)
    "title_vocab": True,                    # also list the picture's title + subtitle as a vocabulary item
}

# Friendly language name -> Tesseract language codes ("+eng" helps mixed text).
LANGS = {"Turkish": "tur+eng", "Urdu": "urd+eng", "Arabic": "ara+eng",
         "Persian": "fas+eng", "English": "eng"}
# Status label shown on each queue card / result card.
ICON = {"waiting": "○ Waiting", "working": "◌ Working…", "done": "✓ Done", "error": "⚠ Error"}
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")


def load() -> dict:
    """Read config.json merged over DEFAULTS (falls back to DEFAULTS on any error)."""
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return dict(DEFAULTS)


cfg = load()   # shared, mutable settings object used by the whole app


def save_cfg() -> None:
    """Persist the current settings."""
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


save = save_cfg   # short alias
