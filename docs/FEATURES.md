# Features

[← Back to main README](../README.md) · Previous: [Project Overview](PROJECT_OVERVIEW.md) · Next: [OCR Modes](OCR_MODES.md)

![UI concept](../assets/ui-mockup.png)

*Early design mockup. The real application is shown in the [main README](../README.md).*

## 1. Input
Add Images (multi-select) · Add Folder · Paste (button or `Ctrl+V`) · Screenshot (drag a rectangle) ·
✂ **Select Area** on any picture. Batch limit 5 / 10 / 20 / 50 / 100 with Remove Selected / All / Undo.

## 2. Image queue
Numbered thumbnails (**Image 1, 2, 3…**), status (Waiting / Working / Done / Error), ▲ ▼ reordering.
Numbers update automatically when images are deleted, undone or moved.

## 3. Three OCR modes → [OCR Modes](OCR_MODES.md)
**Smart** (structure → table) · **Raw** (every word) · **AI Smart** (title, headings, subheadings, bullets).

## 4. Per-image result cards (panel 3)
Thumbnail, *Image N* title, file name, status, editable text, break line between images, and per-image
**Copy · ↻ Raw · ↻ Smart · ↻ AI · ⇄ Swap · 🗑**. Panel buttons: Copy Selected / All / Plain / Original OCR, Clear,
🧩 Combine → Editor.

## 5. Text Editor (panel 4) → [Text Editor](EDITOR.md)
Automatic *Image N → title → headings → bullets* · bold, italic, underline, strike, size, colour, highlight ·
bullets, numbering, alignment, separator · find & replace · sort A–Z · remove duplicates · zoom · focus mode ·
protected user edits with Restore · export MD / TXT / HTML / DOCX / CSV.

## 6. Smart OCR engine → [Smart OCR](SMART_OCR.md)
Word positions + confidence, grid / pair / heading detection, caption and watermark rejection, missing-cell
recovery, language-aware second reading of each cell (ş ı ğ ç), phone-UI noise filter, dark-theme handling.

## 7. Local AI (optional) → [Local AI](LOCAL_AI.md)
Ollama on your own PC: AI Smart mode plus editor buttons *Learn This, Clean, Table, Translate, Explain,
Vocabulary, Flashcards*. No account, no API key, no cloud; only localhost is allowed.

## 8. Settings
Learning language, your language, level, batch limit, minimum OCR confidence, theme, Ollama address and model,
**Test AI connection**. Saved in `config.json` next to the app.

## 9. Portable & safe → [Security](SECURITY.md)
One folder with an `.exe`; no installer, admin rights, registry entries or auto-start; pinned dependencies,
checksums, Defender scan in the build.
