# User Guide

[← Back to main README](../README.md) · Previous: [Installation](INSTALLATION.md) · Next: [Testing](TESTING.md)

## The window — four panels
```text
┌ 1 INPUT ────┬ 2 PREVIEW ───┬ 3 OCR RESULTS ───────┬ 4 TEXT EDITOR ──────────────────┐
│ Add / Shot  │  picture     │ Image 1  [thumb]     │ style  B I U S  A− 13 A+        │
│ Paste/Folder│              │  Copy ↻Raw ↻Smart…   │ • List 1. List ⬅ ↔ ➡ 🎨 ― 🖍    │
│ Batch 3/20  │ OCR mode:    │  ┌ table / text ───┐ │ ↶ ↷ 🔍 Sort  No dup  ⟳ ⤺        │
│ 1. a.jpg ▲▼ │ Smart|Raw|AI │  └─────────────────┘ │ AI: Learn This · Clean · Table  │
│     … Auto-update  ◀ Focus      │
│ 2. b.jpg ▲▼ │ 🔍 Extract   │ ──────────────────── │ ┌─────────────────────────────┐ │
│ 🗑 ↶        │ ✂ Select Area│ Image 2 …            │ │ Image 1  (title)            │ │
│ ⚡ Process  │ ⚙ Settings   │ Copy All · Combine → │ │ Main title / headings       │ │
│   All       │              │                      │ │ • word — translation        │ │
└─────────────┴──────────────┴──────────────────────┴─┴─────────────────────────────┴─┘
```
Drag the thin dividers to resize panels, or press **◀ Focus** (panel 4) to hide panels 1–3.

## First-time setup
1. **⚙ Settings** → learning language (this picks the OCR language), your language, level.
2. *(Optional)* install Ollama for AI → [Local AI](LOCAL_AI.md) → **Test AI connection**.

## Quick workflows
### A. Many flashcards → finished notes
1. **＋ Add Images** (select up to 20) or **📂 Add Folder**.
2. Choose **Smart** and press **⚡ Process All**.
3. Watch the cards fill in panel 3 and the **editor** build itself (*Image 1 → title → vocabulary bullets*).
4. Check each card; use **⇄ Swap** if its columns are reversed.
5. Polish in the editor, then **DOCX / HTML / MD / CSV**.

### B. One part of a picture only
1. Click the image, press **✂ Select Area**, drag a box, drag more boxes, press **Done**.
2. Each box is an *Image N* with its own card.

### C. Polished notes with headings (needs local AI)
1. Choose **AI Smart** → **Process All** (it can take a minute per image).
2. The editor shows *Main title → headings → subheadings → bullets*.

### D. Get every word
Choose **Raw** → **Process All**, or press **↻ Raw** on one card.

## Managing the queue
| Action | How |
|--------|-----|
| Preview | click a card (double-click the preview = Select Area) |
| Reorder | ▲ ▼ — numbering follows |
| Remove | tick boxes → **🗑 Selected** (nothing ticked = previewed image) · card **🗑** · **🗑 All** |
| Undo | **↶ Undo** puts removed images back in their old positions |
| Limit reached | remove an image, process the batch, or raise the limit in Settings |

## Result cards (panel 3)
Each card's text is **editable**. Editing a Smart table (fix a word) also updates the editor, because the editor
re-reads the table. **Copy** copies that card; the buttons below copy all images (Markdown, plain, or original OCR).

## Editor (panel 4)
Full guide: [Text Editor](EDITOR.md). In one line: format, tidy (sort / duplicates / find), export.

## Tips for better OCR
* Higher resolution = better OCR; avoid shrunk images.
* Choose the right **learning language** in Settings before processing.
* If a grid is crowded, use **✂ Select Area** on one row or column.
* If Smart missed something, press **↻ Raw** on that card to see every word.
* Local AI output can be wrong — check it, especially rare words and Urdu / Arabic / Persian diacritics.

## Privacy
OCR stays on your PC. The optional AI talks only to Ollama on `localhost`. Nothing is uploaded.
