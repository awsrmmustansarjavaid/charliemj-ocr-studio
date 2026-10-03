<!--
  README.md - main entry point of the repository.
  Short overview + quick start. Detailed documents live in the docs/ folder.
-->

<p align="center">
  <img src="assets/banner.png" alt="Charlie MJ OCR & Language Studio" width="100%">
</p>

<h1 align="center">Charlie MJ OCR &amp; Language Studio</h1>

<p align="center">
  <b>A lightweight, portable Windows OCR tool that turns flashcards and screenshots into clean, organised study tables — with optional local AI.</b>
</p>

<p align="center">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11-yellow">
  <img alt="OCR" src="https://img.shields.io/badge/OCR-Tesseract%20(offline)-green">
  <img alt="AI" src="https://img.shields.io/badge/AI-Ollama%20(local%2C%20optional)-8b5cf6">
  <img alt="Network" src="https://img.shields.io/badge/network-localhost%20only-success">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

<p align="center">
  <a href="./CharlieMJ-OCR-Portable/CharlieMJ-OCR-Portable.zip">
    <img src="https://img.shields.io/badge/⬇️%20Download-CharlieMJ--OCR--Portable-blue?style=for-the-badge" alt="Download CharlieMJ-OCR-Portable">
  </a>
</p>

---

## What is it?

Typing every word from a flashcard by hand is slow, and normal OCR gives you a messy block of text. **Charlie MJ OCR & Language Studio** reads the *layout* of the picture, so a Turkish label and the English text under it end up side by side — and then gives you a **text editor** to turn the result into finished study notes:

![Smart OCR before and after](assets/smart-ocr-before-after.png)

> **Image → OCR with word positions → structure detection → clean table → (optional local AI) → Text Editor → Copy / Export**

![Application](assets/app-screenshot.png)

## Key features

- 🧠 **Three OCR modes** — **Smart** (structure → clean *Original | Translation* table), **Raw** (every word, nothing filtered) and **AI Smart** (local AI writes a main title, headings, subheadings and bullet vocabulary). → [OCR Modes](docs/OCR_MODES.md)
- ✂ **Select Area tool** — drag a box on the picture; each box becomes its own *Image N* and is OCR'd at once.
- 📝 **Text Editor (panel 4)** — results flow in automatically as **Image N → main title → headings → bullets**; format with bold, italic, underline, size, colour, highlight, lists, alignment; find & replace, sort A–Z, remove duplicates; export **MD / TXT / HTML / DOCX / CSV**. → [Text Editor](docs/EDITOR.md)
- 🔢 **One result per image** — cards titled **Image 1, Image 2, …** with a thumbnail, break lines between images and per-image *Copy, Raw, Smart, AI, Swap, Delete*. Numbers update automatically when you delete or reorder (▲ ▼).
- 📸 **Input** — add many images, a folder, paste from the clipboard, or drag a screenshot area. Batch limit (default 20), Remove / Remove All / Undo.
- 🎯 **Accurate on real posters** — ignores phone UI, captions and watermarks, recovers cells the first pass missed, never cuts words short. → [Smart OCR](docs/SMART_OCR.md)
- 🤖 **Local AI (optional, no cloud)** — through [Ollama](https://ollama.com): Learn This, Clean, Table, Translate, Explain, Vocabulary, Flashcards. No account, no API key, text never leaves your PC. → [Local AI](docs/LOCAL_AI.md)
- 🔒 **Safe by design** — offline OCR, localhost-only AI, no installer, no admin rights, no startup entries, pinned dependencies, checksummed builds. → [Security](docs/SECURITY.md)
- 🪶 **Lightweight & portable** — about 100–150 MB, runs from a USB drive.

Full list: [docs/FEATURES.md](docs/FEATURES.md) · What changed: [docs/CHANGELOG.md](docs/CHANGELOG.md)

## Quick start

### Option A — Get the `.exe` from GitHub (no installs)
1. Upload this repository to your GitHub account (keep the hidden `.github` folder).
2. Open the **Actions** tab → **Build Windows portable EXE** → **Run workflow**.
3. After ~10 minutes download the **CharlieMJ-OCR-Portable** artifact, unzip it and run **`CharlieMJ-OCR.exe`**.
4. *(Optional)* put the zip in [`CharlieMJ-OCR-Portable/`](CharlieMJ-OCR-Portable/README.md) so the download button at the top works.

### Option B — Build it yourself
Install Python 3.11, put Tesseract + language data in a `tesseract/` folder, then double-click **`build.bat`**.

### Option C — Run from source
```bash
pip install -r requirements.txt
python main.py
```

### Optional: local AI
Install Ollama from [ollama.com](https://ollama.com), run `ollama pull gemma3:4b`, then press **Settings → Test AI connection**. OCR and the editor work without it.

Step-by-step details and troubleshooting: [docs/INSTALLATION.md](docs/INSTALLATION.md)

## How to use

1. **⚙ Settings** → choose your learning language and your language.
2. Add images (**＋ / 📸 / 📋 / 📂**) — or open one and press **✂ Select Area**.
3. Choose **Smart**, **Raw** or **AI Smart**, then **⚡ Process All** (or **🔍 Extract Text** for one image).
4. Check each **Image N** card; use **⇄ Swap** if the columns are reversed.
5. The **editor** fills itself — format it, then **Copy** or export **DOCX / HTML / MD / CSV**.

More: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

## Technology

Python 3.11 · CustomTkinter · Pillow · Tesseract (pytesseract) · Ollama (local AI, optional) · PyInstaller · GitHub Actions. Why these were chosen (and why PaddleOCR was not bundled): [docs/TECHNOLOGIES.md](docs/TECHNOLOGIES.md)

## Documentation

| Document | What you will find |
|----------|--------------------|
| [Project Overview](docs/PROJECT_OVERVIEW.md) | What the program is, why it was built, goals |
| [Features](docs/FEATURES.md) | Complete feature list |
| [OCR Modes](docs/OCR_MODES.md) | Smart, Raw, AI Smart and the Select Area tool |
| [Text Editor](docs/EDITOR.md) | The 4th panel: automatic notes, formatting, tools, export |
| [Smart OCR](docs/SMART_OCR.md) | How messy pictures become clean tables |
| [Local AI](docs/LOCAL_AI.md) | Ollama setup, models, AI buttons, troubleshooting |
| [Technologies](docs/TECHNOLOGIES.md) | Tech stack and the reasons behind it |
| [Architecture](docs/ARCHITECTURE.md) | Modules, data flow, threading, editor model, diagrams |
| [Security](docs/SECURITY.md) | Privacy, antivirus false positives, verifying downloads |
| [Installation](docs/INSTALLATION.md) | Build the `.exe`, requirements, troubleshooting |
| [User Guide](docs/USER_GUIDE.md) | Workflows, buttons, tips |
| [Testing](docs/TESTING.md) | Unit, integration and end-to-end UI tests |
| [Changelog](docs/CHANGELOG.md) | What is new in each version, and what was fixed |
| [Roadmap](docs/ROADMAP.md) | Planned versions and ideas |

## Repository structure

```text
charliemj-ocr-studio/
├── README.md                    ← you are here
├── main.py                      ← entry point
├── app/                         ← the application package
│   ├── config.py                   settings, paths, constants
│   ├── layout.py                   structure detection (pure Python, unit-tested)
│   ├── ocr_engine.py               Tesseract: words + positions, Raw text, cell re-reading
│   ├── richtext.py                 editor document model + MD/TXT/HTML/DOCX exporters (pure Python)
│   ├── editor.py                   the formatted text editor panel
│   ├── selector.py                 the ✂ Select Area tool
│   ├── prompts.py                  instructions for the local AI
│   ├── local_ai.py                 optional local AI (Ollama, localhost only)
│   └── ui.py                       the main window (4 panels)
├── tests/                       ← unit, integration and end-to-end UI tests
├── docs/                        ← detailed documentation (table above)
├── assets/                      ← banner, diagrams, screenshots
├── CharlieMJ-OCR-Portable/      ← where the built zip goes (download button)
├── requirements.txt             ← pinned runtime dependencies
├── requirements-build.txt       ← + PyInstaller (build only)
├── build.bat                    ← local build of the portable .exe
├── version_info.txt             ← publisher info embedded in the .exe
├── .github/workflows/build.yml  ← cloud build + tests + Defender scan + checksums
├── .gitignore  ·  LICENSE
```

## Privacy & security

- OCR runs **entirely on your PC**.
- The optional AI talks only to **Ollama on localhost**; other addresses are refused by the code.
- No API keys, no accounts, no telemetry, no auto-start, no admin rights.
- Antivirus programs sometimes flag *any* unsigned PyInstaller `.exe`. How the build minimises that, and how to verify your download: [docs/SECURITY.md](docs/SECURITY.md).

## Known limitations

- Smart OCR relies on geometry: very crowded or decorative layouts may need **⇄ Swap**, **✂ Select Area** or a manual edit.
- Tesseract can struggle with stylised fonts and some Arabic-script text; Raw and AI Smart can help. Local AI is only as good as your model — always double-check it.
- The editor's bullets are text characters (not Word list objects) and the clipboard receives plain text; use HTML / DOCX export to keep formatting.
- The `.exe` is not code-signed, so Windows SmartScreen may warn on first launch.

## License

Released under the [MIT License](LICENSE).
