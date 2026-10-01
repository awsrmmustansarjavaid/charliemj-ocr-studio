# Testing

[← Main README](../README.md) · Previous: [Security](SECURITY.md) · Next: [Roadmap](ROADMAP.md)

## What is tested

| Layer | File | Needs | Covers |
|-------|------|-------|--------|
| Unit tests | `tests/test_layout.py` | Python only | Card grid → table, two-column table, Urdu/Arabic orientation, noise removal, plain paragraphs, swap, CSV pair extraction, empty input |
| UI smoke test | `tests/smoke_ui.py` | Tesseract + a display | The real window end to end (see below) |

## Run the unit tests (any OS)

```bash
python -m unittest discover -s tests -v
```
`build.bat` and the GitHub workflow run them automatically before building the `.exe`.

## Run the UI smoke test

```bash
# Linux (virtual display) - needs tesseract-ocr with tur+eng, python3-tk, xvfb
xvfb-run -a python tests/smoke_ui.py path/to/image1.png path/to/image2.png
# Windows / macOS (real display)
python tests/smoke_ui.py image1.png image2.png
```

It opens the real window and checks:

1. Images are queued and **Process All** produces a result for each.
2. Combined text has **`## Image N`** headings and **`---`** between images.
3. **Reordering** changes the numbering.
4. **⇄ Swap** changes the table and swaps back.
5. **Delete + Undo** restore the queue.
6. **Combine All OCR** fills the Combined tab.
7. **CSV export** contains the pairs with duplicates removed.
8. The **local AI** buttons (text action and vision OCR) work against a tiny **fake Ollama server** — no model needed.
9. The **privacy guard** refuses non-local AI addresses.

Set `SHOT=/path/screenshot.png` to also save a screenshot of the window.

## What has *not* been verified

- Accuracy on **your** photos: the tests use generated images that imitate a "Types of Gloves" card grid and a two-column table. Real photos vary — send examples that fail and add them as tests.
- Real Ollama models (the AI buttons are tested against a stand-in server).
- The Windows `.exe` itself is built by the GitHub workflow; the same code was packaged and launched with PyInstaller on Linux during development.
