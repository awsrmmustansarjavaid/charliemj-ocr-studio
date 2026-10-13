# Technologies

[← Main README](../README.md) · Previous: [Local AI](LOCAL_AI.md) · Next: [Architecture](ARCHITECTURE.md)

| Layer | Technology | Role |
|---|---|---|
| Language | Python 3.11 | Application runtime |
| GUI | CustomTkinter / Tkinter | Four-panel desktop UI |
| Images | Pillow | Loading, screenshots, clipboard, scaling and crops |
| OCR | Tesseract 5 + pytesseract | Offline OCR, positions and confidence |
| Structure | Python standard library (`layout.py`) | Pairing, grids, headings and recovery logic |
| Local AI | Ollama + Python `urllib` | Optional AI Smart and study agents |
| Packaging | PyInstaller | Portable Windows one-folder EXE |
| CI | GitHub Actions | Windows build, tests, smoke test, Defender scan and checksums |

Runtime Python packages are pinned in `requirements.txt`: CustomTkinter, Pillow and pytesseract. The local AI HTTP client uses Python's built-in `urllib`.

## Why Tesseract

Tesseract already provides word positions and confidence, which are the inputs the deterministic Smart OCR layout engine needs. Keeping the engine small also keeps the portable build easier to audit.

## Why local Ollama

The project does not bundle a multi-gigabyte model and does not send study images to a cloud AI API. Ollama is separate, local and model-selectable. If it is unavailable, OCR continues to work.

## Why one-folder PyInstaller

The executable, Python runtime, Tesseract and `config.json` can travel together. The build disables UPX compression and creates a checksum manifest.

## Language data

The workflow bundles English, Turkish, Urdu, Arabic and Persian Tesseract data. The application can discover installed packs and download additional official `tessdata_fast` packs on demand.

## Build reproducibility

Dependencies are pinned, tests run before packaging, and the workflow smoke-tests the actual frozen EXE. This catches import/package errors that a source-only test would miss.
