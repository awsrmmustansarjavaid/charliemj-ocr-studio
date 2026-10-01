# Technologies

[← Main README](../README.md) · Previous: [Local AI](LOCAL_AI.md) · Next: [Architecture](ARCHITECTURE.md)

## Stack at a glance

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | **Python 3.11** | Fast development, great imaging libraries |
| GUI | **CustomTkinter** (on Tkinter) | Modern dark/light widgets, far lighter than Qt or Electron |
| Images | **Pillow** | Loading, screenshots, clipboard, thumbnails, pre-processing |
| OCR | **Tesseract 5** via **pytesseract** | Offline text + word positions + confidence |
| Layout | **Own code** (`app/layout.py`, standard library only) | Finds pairs, tables, titles from word positions |
| Local AI | **Ollama** over HTTP (`urllib`) | Optional cleanup, translation, vocabulary, vision OCR |
| Packaging | **PyInstaller** (one-folder, no UPX) | Portable `.exe` folder |
| CI/CD | **GitHub Actions** | Reproducible cloud build, tests, Defender scan, checksums |
| Docs | **Markdown**, **Mermaid**, **SVG** | Render natively on GitHub |

Runtime dependencies: only **three** Python packages (customtkinter, pillow, pytesseract), all version-pinned.

## Key decisions

### Why Tesseract and not PaddleOCR?
[PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) is excellent and was evaluated, especially for its **word boxes + confidence, layout analysis and table recognition** — those *ideas* are what Smart OCR implements. Shipping PaddleOCR itself was rejected for this project because:

- it needs the PaddlePaddle runtime (hundreds of MB) — against the "lightweight" goal;
- large, many-file Python bundles are **more likely to trigger antivirus false positives** after packaging;
- Turkish/Urdu/Arabic/Persian need separate recognition models to download and ship;
- Tesseract already returns the boxes and confidences the layout step needs, and a small cell re-read step closes most of the accuracy gap.

A lighter ONNX route (e.g. RapidOCR with PaddleOCR models) is a possible optional engine later — see the [Roadmap](ROADMAP.md). The engine is isolated in `app/ocr_engine.py`, so swapping it does not touch the layout code.

### Why Ollama and not a Python AI library or a cloud API?
- A cloud API (the first version used one) needs an account/key, sends your images away, and was the reason "AI OCR" failed for lack of a working key.
- Bundling a model or `llama-cpp`/`torch` would add gigabytes and a big, flag-prone binary.
- **Ollama** is a separate, well-known program: the app stays small, you choose the model, and the app only talks to `127.0.0.1`.
- Calls use Python's built-in `urllib`, so there is **no extra HTTP dependency**.

### Why PyInstaller one-folder, no UPX?
Faster start than one-file mode, Tesseract and `config.json` sit beside the `.exe` (portable), and **UPX-compressed executables are a classic antivirus trigger**, so compression is disabled.

### Why pinned versions?
Pinning protects against a surprise or malicious new release (supply-chain risk) and keeps builds reproducible.

## Approximate size (estimate)

| Part | Size |
|------|------|
| Python runtime + libraries (PyInstaller) | ~60–100 MB |
| Tesseract + 5 fast language models | ~50–90 MB |
| **Total** | **~150–200 MB** (no AI models inside; Ollama models are separate) |

## Third-party licences
Tesseract (Apache 2.0), Pillow (HPND), CustomTkinter (MIT), pytesseract (Apache 2.0), PyInstaller (GPL with bootloader exception). Ollama and its models have their own licences.
