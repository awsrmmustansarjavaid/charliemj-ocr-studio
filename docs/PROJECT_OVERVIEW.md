# Project Overview

[← Main README](../README.md) · Next: [Features](FEATURES.md)

**Charlie MJ OCR & Language Studio v2.3.0** is a portable Windows desktop OCR workspace for language-learning screenshots, flashcards, posters and other image-based vocabulary material.

## What makes it different

Ordinary OCR returns text without its visual relationship. Charlie MJ keeps word positions, detects bilingual structure and can re-read grid cells so a screenshot becomes organised study material instead of one long text block.

The core rule is **extract completely first, organise second**. Smart structure, AI formatting and deduplication are downstream transformations; the original Raw OCR remains available.

## Main workflow

1. Add images, a folder, a pasted image or a screenshot.
2. Choose **Smart, Raw or AI Smart** and **Fast, Balanced or Deep**.
3. Process one image or the whole queue.
4. Review each Image N result card and captured areas.
5. Let the editor build study notes, then edit/copy/export.

## Current capabilities

- Unlimited application OCR queue and a unified job pipeline for single-image and batch processing.
- Complete-image OCR with dense-screenshot recovery and grid/cell re-reading.
- Dynamic Tesseract language discovery and on-demand official language-pack installation.
- Select Area with zoom, fit, pan, rotate, crop and multiple boxes.
- Rich text editor with protected user edits, Find/Replace, Sort, duplicate removal, Focus and Restore.
- Markdown, TXT, HTML, DOCX and CSV export.
- Optional local Ollama AI Smart and three local AI agents.
- Portable Windows packaging with bundled Tesseract, tests, EXE startup smoke testing, Defender scan and SHA-256 checksums.

## Design principles

1. **Do not lose OCR information.** Raw remains available and AI omissions are restored from OCR.
2. **Keep OCR deterministic.** Smart structure is based on positions and confidence; AI is optional.
3. **Keep AI local.** Ollama runs on the user's machine.
4. **Keep the app portable.** Settings live beside the executable.
5. **Keep the UI responsive.** OCR and AI work outside the Tkinter UI thread.

## Non-goals

The project is not a cloud OCR service, does not require an online account, and is not intended to replace a full spaced-repetition platform.

See [Architecture](ARCHITECTURE.md), [OCR Modes](OCR_MODES.md), [User Guide](USER_GUIDE.md) and [Roadmap](ROADMAP.md) for details.
