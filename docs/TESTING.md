# Testing

[← Back to main README](../README.md) · Previous: [User Guide](USER_GUIDE.md) · Next: [Roadmap](ROADMAP.md)

Run everything: `python -m unittest discover -s tests -v`   ·   UI test: `xvfb-run -a python tests/smoke_ui.py` (Linux)
or `python tests/smoke_ui.py` (Windows, with a display).

| File | What it checks | Needs |
|------|----------------|-------|
| `tests/test_layout.py` | structure detection on synthetic word boxes: columns, pairs, orientation, noise, text fallback, Markdown round-trip, empty input | nothing |
| `tests/test_richtext.py` | Markdown → blocks, tables → bullets, exports (MD / TXT / HTML), **DOCX is valid** (zip + XML), vocabulary pairs | nothing |
| `tests/test_ocr_integration.py` | **real Tesseract** on a generated vocabulary poster: ≥ 11 / 12 pairs, no fake title, no caption rows, **Raw contains every word** | Tesseract (skipped if missing) |
| `tests/smoke_ui.py` | the real window driven like a user (see below) | a display (Xvfb) + Tesseract |
| `tests/make_poster.py` | helper: builds the test poster (3×5 photo grid, watermark, phone UI, caption) | Pillow |

## What the UI smoke test covers
Starts a **fake Ollama server**, then: opens images → Smart *Process All* → checks the editor was built automatically
(*Image 1* title, main title, *Vocabulary*, bullets, separators) → **Raw** contains every word → **AI Smart** produces
h1 / h2 / h3 + bullets → **Select Area** inserts a new *Image N* → reordering renumbers the editor → **Swap** → typing
in the editor protects it from automatic updates, **Update** and **Restore** → an editor **AI button** → exports
(MD, TXT, HTML, DOCX, CSV with image numbers) → the selection window with simulated mouse events → **Focus** mode →
the AI status label.

## In CI
`.github/workflows/build.yml` runs `test_layout` and `test_richtext` (blocking) and `test_ocr_integration`
(informational) before building the `.exe`.

## Manual checklist before a release
1. Process 2–3 of your own screenshots in each mode.
2. Select Area on a crowded picture; delete / reorder images and watch the numbers.
3. Format something in the editor, export DOCX, open it in Word.
4. With Ollama running: AI Smart and one AI button. Without Ollama: AI Smart falls back to Smart.
5. Verify the download against `SHA256SUMS.txt` ([Security](SECURITY.md)).
