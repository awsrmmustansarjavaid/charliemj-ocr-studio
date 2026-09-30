# Technologies

[← Back to main README](../README.md) · Previous: [Features](FEATURES.md) · Next: [Architecture](ARCHITECTURE.md)

## Stack at a glance

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | **Python 3.11** | Fast to develop; excellent OCR/imaging libraries |
| GUI | **CustomTkinter** (on Tkinter) | Modern dark/light widgets, far lighter than Qt or Electron |
| Images | **Pillow (PIL)** | Loading images, screenshots, clipboard, thumbnails, pre-processing |
| OCR | **Tesseract OCR** via **pytesseract** | Offline text recognition for many languages |
| AI | **Google Gemini API** via **requests** | Optional cleanup, translation, vocabulary, flashcards, vision OCR |
| Packaging | **PyInstaller** (one-folder mode) | Creates the portable `.exe` folder |
| CI/CD | **GitHub Actions** | Builds the Windows `.exe` in the cloud |
| Docs | **Markdown**, **Mermaid**, **SVG** | Documentation and diagrams that render on GitHub |

## Why these choices?

### Python + CustomTkinter
Tkinter ships with Python, so there is no extra runtime. CustomTkinter adds rounded, themeable widgets so the app looks modern. Alternatives such as Electron (hundreds of MB) or PyQt (larger, licensing considerations) were rejected to keep the app **lightweight**.

### Tesseract (not PaddleOCR)
- **Pros:** fully offline, small per-language files (a few MB), stable Windows binaries, supports Turkish, Urdu, Arabic and Persian.
- **Cons:** weaker on stylised fonts and some Arabic-script text.
- **Mitigation:** the optional **AI OCR** button uses Gemini vision for hard images. RapidOCR (ONNX) is a lighter upgrade path than PaddleOCR if better local accuracy is needed later.

### Gemini via plain REST
The app calls the HTTPS endpoint directly with `requests`, avoiding a large SDK dependency. The user supplies their own API key (free tier available), so there is no server, account or cost for the author.

### PyInstaller one-folder mode
Faster startup than one-file mode (which unpacks to a temp folder each launch), and it keeps Tesseract and `config.json` beside the `.exe`, which is what makes the app portable.

## Approximate size

| Part | Size |
|------|------|
| Python runtime + libraries (PyInstaller) | ~50–80 MB |
| Tesseract + 5 fast language models | ~40–70 MB |
| **Total** | **~100–150 MB** |

## Third-party licences

Tesseract (Apache 2.0), Pillow (HPND), CustomTkinter (MIT), requests (Apache 2.0), PyInstaller (GPL with bootloader exception), pytesseract (Apache 2.0). Gemini use is subject to Google's terms.

See [Architecture](ARCHITECTURE.md) for how these pieces fit together.
