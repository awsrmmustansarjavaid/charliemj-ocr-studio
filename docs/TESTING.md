# Testing

[← Back to main README](../README.md) · Related: [Smart OCR](SMART_OCR.md) · [Architecture](ARCHITECTURE.md)

The project has **three layers of tests**. All of them run on Windows (in the GitHub build) and on Linux.

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v          # 26 unit + integration tests
python tests/smoke_ui.py                         # end-to-end test of the real window (needs a display)
```

The GitHub workflow runs `python -m unittest tests.test_layout tests.test_richtext` (**blocking**: the build stops if one fails) and
`python -m unittest tests.test_ocr_integration` (**informational**: a font or Tesseract difference on the runner must not block the
`.exe`). The test files add their own folder to the import path, so every way of starting them works.

## 1. Unit tests (no GUI, no OCR)

| File | What it checks |
|------|----------------|
| `tests/test_layout.py` | segments, noise filter, card grids, two-column tables, orientation (Urdu script), empty input, Markdown round trip, **grid completion** (a missing row *and* column are recovered), phone-interface text is never taken for a row, **title counted as vocabulary**, **AI safety net** (`merge_missing`) |
| `tests/test_richtext.py` | Markdown → blocks, tables → bullets, Markdown / plain text / HTML export, vocabulary pairs for CSV, **DOCX is a valid zip with well-formed XML** |

## 2. Integration tests (real Tesseract)

`tests/test_ocr_integration.py` is skipped automatically when Tesseract is not installed. It generates test pictures
(`tests/make_poster.py`, Pillow only) and runs the real OCR:

| Test | Picture | Expectation |
|------|---------|-------------|
| Poster, Smart | 3 × 5 photo grid, watermark, phone UI, caption | ≥ 11 of 12 pairs exact, no title from "Posts", caption is not a row |
| Poster, Raw | same | every word of the poster is in the Raw text |
| **Glove card, Smart** | 4 × 3 grid, labels almost touching, watermark, title + subtitle | **all 12 cells exact, title + subtitle exact, grid 3 × 4, 0 unread cells** |
| **Glove card, notes** | same | **13 vocabulary bullets** (12 pictures + the title) |
| Glove card, Raw | same | every word, with the right accents |

## 3. End-to-end window test

`tests/smoke_ui.py` starts the real application (headless with `xvfb-run` on Linux) with a fake local-AI server and walks through:

1. Smart **Process All** → results in the cards and the editor (*Image 1 → heading → bullets*, separators)
2. **Raw** mode → complete text, *Raw text* heading in the editor
3. **AI Smart** (fake model) → h1 / h2 / h3 + bullets; AI that forgets a word → the word is added back
4. **Select Area → This image**: no new image, an *Area 1* record, *Area 1* under *Image 1* in the editor, no batch slot used
5. **Select Area → New image** and removing an area
6. reorder → *Image N* renumbers in cards and editor
7. **Swap** columns · edit protection (your edits are not overwritten) · **⤺ Restore** · forced update
8. exports: Markdown, TXT, HTML, DOCX, CSV · focus mode · AI status
9. the **selector window** with simulated mouse: zoom, Fit, Fit width, 100 %, drag a box, **crop**, **rotate**, undo edit

## Manual checklist before a release
1. Process 20 real flashcards in **Balanced**; compare the count of phrases with the pictures; re-run doubtful ones in **Deep**.
2. Select Area on a tall screenshot: zoom, fit, pan, send a box to *This image*; check cards and editor.
3. Delete and reorder images and watch the numbers.
4. Export DOCX / HTML and open them; import the CSV in a spreadsheet.
5. With Ollama stopped, run **AI Smart**: the Smart result must appear with a message.
