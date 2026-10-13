# Features

[← Main README](../README.md) · Previous: [Project Overview](PROJECT_OVERVIEW.md) · Next: [OCR Modes](OCR_MODES.md)

## Input and queue

- Add multiple images, add a folder, paste an image, or capture a screenshot.
- Unlimited application queue; images can be reordered, removed and restored with Undo.
- `F5` processes the queue, `Ctrl+O` adds images and `Ctrl+Enter` re-runs the selected image.
- Progress, status and diagnostics show which image is running.

## Three OCR modes

- **Smart** — complete-image OCR followed by deterministic structure detection, bilingual pairing, heading detection and grid/cell recovery.
- **Raw** — complete OCR text with no Smart layout filtering.
- **AI Smart** — Smart OCR plus optional local Ollama formatting into titles, headings, subheadings and vocabulary bullets.

All three modes share the same OCR job pipeline for batch and per-image buttons.

## Accuracy levels

- **Fast** — first OCR pass.
- **Balanced** — first pass plus cell re-reading and targeted dense-screenshot recovery.
- **Deep** — additional language-specific voting and larger-scale retry for difficult cells.

The goal is complete screenshot coverage first; organisation and deduplication happen after extraction.

## Language support

Tesseract languages are discovered from installed language packs. The portable build starts with English, Turkish, Urdu, Arabic and Persian data, and additional official `tessdata_fast` packs can be installed on demand.

## Select Area

Zoom, fit, fit-width, 100%, pan, rotate, crop and draw multiple boxes. By default each captured area is added to its source image and does not create a separate queue entry.

## OCR result cards

Each image has its own editable result card with thumbnail, status and **Copy / Smart / Raw / AI / Swap / Area / Delete** controls. Original OCR remains available through **Copy Original OCR**.

## Text Editor

Automatically builds Image N sections, headings and vocabulary bullets. Includes rich formatting, find/replace, sorting, duplicate removal, focus mode, protected user edits and Restore. Exports MD, TXT, HTML, DOCX and CSV.

## Local AI

Ollama is optional and local-only. AI Smart has a lossless OCR safety net. Local AI Agents include OCR Structure, Vocabulary and Study Tutor.

## Portable Windows build

No installer or admin rights are required. The Windows workflow bundles Tesseract, runs tests, smoke-tests the frozen EXE, performs a Defender scan when available and writes SHA-256 checksums.
