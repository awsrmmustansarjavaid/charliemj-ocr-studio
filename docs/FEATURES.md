# Features

[← Back to main README](../README.md) · Previous: [Overview](PROJECT_OVERVIEW.md) · Next: [Technologies](TECHNOLOGIES.md)

![UI concept](../assets/ui-mockup.png)

*Design mockup of the full vision. Version 1 implements the capture, OCR, notes and AI screens; the remaining screens are on the [Roadmap](ROADMAP.md).*

## Implemented in v1

### 1. Image input
| Feature | Description |
|---------|-------------|
| Add Images | Multi-select file dialog (PNG, JPG, JPEG, WEBP, BMP, TIFF) |
| Add Folder | Adds every supported image in a folder, up to the batch limit |
| Paste Image | Pastes a bitmap from the clipboard (e.g. after `Win+Shift+S`) or copied image files; `Ctrl+V` also works |
| Screenshot | Hides the window, freezes the screen, and lets you drag a rectangle; `Esc` cancels |

### 2. Image queue
- Thumbnail card for each image with a status: **Waiting → Working → Done / Error**.
- Live counter: `Batch: 7 / 20`.
- **Batch limit** selectable in Settings (5, 10, 20, 50, 100); a warning appears when it is reached.
- **Remove Selected** (tick the checkboxes, or the previewed image), **Remove All** (with confirmation), **Undo**.
- **Process All** runs OCR on every pending image in a background thread; a failure on one image does not stop the rest.

### 3. Local OCR
- Powered by bundled **Tesseract**; works **offline**.
- Languages: Turkish, Urdu, Arabic, Persian, English (mixed with English for better accuracy).
- Automatic pre-processing: grayscale, auto-contrast, 2× upscale of small images.

### 4. Notes editor
- Buttons: **Title, H1, H2, H3, Bullet, Numbered list, Bold, Italic, Separator line, Undo, Redo**.
- Uses Markdown syntax (`#`, `##`, `-`, `**bold**`), so notes stay readable anywhere.
- Each OCR result is appended under a `## filename` heading.

### 5. Copy and export
| Button | What it does |
|--------|--------------|
| Copy Selected | Copies only the highlighted text |
| Copy All | Copies all notes (Markdown) |
| Copy Plain | Copies notes without Markdown symbols |
| Copy Original OCR | Copies the raw OCR text before any editing/AI |
| Save / Export TXT / Export CSV | `.md`, `.txt`, or `Front,Back` CSV for Anki |

The CSV exporter detects lines shaped like `- **word** — meaning` and **removes duplicates**.

### 6. Optional AI (Google Gemini)
| Button | Result |
|--------|--------|
| ✨ Learn This | Title, cleaned text, translation, vocabulary, grammar note |
| Clean | Fixes OCR errors and organises text into headings/bullets (replaces the selection) |
| Translate | Translates into your chosen language |
| Explain | Meaning, pronunciation, base form, part of speech, examples |
| Vocabulary | Level-appropriate word list |
| Flashcards | Front/back cards ready for CSV export |
| 🤖 AI OCR | Sends the image to Gemini vision — useful for difficult fonts or scripts |

AI acts on the **selected text** (or everything if nothing is selected). See the [AI Guide](AI_GUIDE.md).

### 7. Settings
Learning language, your language, level, batch limit, theme (dark/light), Gemini API key and model — saved to `config.json` next to the app.

### 8. Portability
Runs from any folder or USB drive on Windows; no installer or admin rights.

## Planned (not in v1)
Vocabulary library with Know / Learning tracking, flashcard review with spaced repetition, progress dashboard, pronunciation practice, global hotkey capture, drag-and-drop, PDF OCR, and more — see the [Roadmap](ROADMAP.md).
