# Features

[← Main README](../README.md) · Previous: [Overview](PROJECT_OVERVIEW.md) · Next: [Smart OCR](SMART_OCR.md)

![App screenshot](../assets/app-screenshot.png)

*A real screenshot of version 1.1: the card grid on the left was turned into the table on the right.*

## 1. Image input
| Feature | Description |
|---------|-------------|
| Add Images | Multi-select dialog (PNG, JPG, JPEG, WEBP, BMP, TIFF) |
| Add Folder | Adds every supported image in a folder, up to the batch limit |
| Paste Image | Bitmap from the clipboard (e.g. after `Win+Shift+S`) or copied image files; `Ctrl+V` works too |
| Screenshot | Hides the window, freezes the screen, drag a rectangle; `Esc` cancels |

## 2. Image queue
- Numbered cards (**1., 2., 3., …**) with thumbnail and status: Waiting → Working → Done / Error.
- Counter `Batch: 7 / 20`; limit selectable (5–100) in Settings.
- **▲ ▼** buttons reorder images. **Remove Selected / Remove All / Undo** (restores the old positions).
- **Process All** OCRs every pending image in the background and shows progress (`Processing 3 / 20`). One failing image never stops the batch.

## 3. Smart OCR (the main feature)
- Reads **word positions and confidence**, not just text → [details](SMART_OCR.md).
- Detects **bilingual tables** (label + translation under it, or two columns), titles/subtitles, and plain paragraphs.
- Puts the **learning language in column 1** and the translation in column 2 (script/letter hints, with a **⇄ Swap** button).
- Removes UI noise (icons, clock, stray symbols) and re-reads each cell with its own language model so letters like **ş ı ğ ç ü ö** come out right.
- **Raw mode** gives plain OCR text when you do not want structure.

## 4. One result card per image
- Title **Image 1, Image 2, …** (numbers follow the queue; deleting or reordering renumbers automatically).
- Thumbnail, file name and status beside each title.
- Per-image buttons: **Copy, ↻ Smart, ↻ Raw, ⇄ Swap, 🗑 Delete**.
- Each result is its own **editable** text box; a horizontal separator line sits between images.
- **🧩 Combine All OCR** joins everything with `## Image N`, the file name, and `---` between images.

## 5. Notes editing
Title, H1–H3, bullet, numbered list, bold, italic, separator line, undo/redo — acting on whichever box you last clicked. Markdown tables are padded so they stay aligned in the monospace boxes.

## 6. Copy and export
| Button | Result |
|--------|--------|
| Copy (per image) | That image's result |
| Copy Selected | Highlighted text of the active box |
| Copy All | All images, numbered, separated by `---` |
| Copy Plain | Same without Markdown symbols and table pipes |
| Copy Original OCR | The untouched OCR text of every image |
| Save (.md) / Export TXT / Export CSV | CSV columns: `Image, <language>, <translation>`, duplicates removed |

## 7. Optional local AI (Ollama)
✨ Learn This · Clean · Translate · Explain · Vocabulary · Flashcards · 📊 Table · 🤖 AI OCR (vision). Runs on your PC, localhost only → [Local AI guide](LOCAL_AI.md). A status line shows whether Ollama is reachable, and Settings has a **connection test**.

## 8. Settings
Learning language, your language, level, default OCR mode, minimum OCR confidence, batch limit, theme, local-AI address and model. Saved in `config.json` beside the app.

## 9. Portable and private
No installer, no admin rights, no telemetry, no cloud, no startup entry → [Security](SECURITY.md).

## Not in v1.1
Drag-and-drop, global hotkey, vocabulary library, spaced repetition, text-to-speech — see the [Roadmap](ROADMAP.md).
