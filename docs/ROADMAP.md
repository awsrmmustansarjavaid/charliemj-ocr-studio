# Roadmap

[← Main README](../README.md) · Previous: [Testing](TESTING.md) · Start: [Overview](PROJECT_OVERVIEW.md)

| Version | Theme | Status |
|---------|-------|--------|
| v1.0 | Basic OCR, queue, notes editor, cloud AI | ✅ Replaced |
| **v1.1** | **Smart OCR tables, per-image cards, local AI (Ollama), security hardening** | ✅ **Current** |
| v1.2 | Drag-and-drop, drag to reorder, crop/rotate before OCR, per-image language override | 📝 Planned |
| v1.3 | Optional second OCR engine (RapidOCR/ONNX with PaddleOCR models) for hard fonts | 💡 Idea |
| v2 | Vocabulary library (SQLite): Know / Learning / Review, duplicates across sessions, search | 📝 Planned |
| v3 | Spaced-repetition review, Anki `.apkg` export | 📝 Planned |
| v4 | Text-to-speech, pronunciation practice | 💡 Idea |
| v5 | Progress dashboard, projects per language, PDF and video-subtitle capture, DOCX/PDF export | 💡 Idea |

## Details

### v1.2 — Faster capture, better control
- **Drag & drop** images into the window; drag cards to reorder (today: ▲ ▼ buttons).
- Crop / rotate / enhance an image before OCR.
- Language override per image (mixed batches).
- Optional code-signed releases to reduce SmartScreen/antivirus warnings.

### v1.3 — Stronger OCR on difficult images
PaddleOCR's models are strong but the framework is heavy. A lighter ONNX runtime (e.g. RapidOCR) could run as an *optional* engine behind the same `ocr_engine` interface, so the layout code stays unchanged. See [Technologies](TECHNOLOGIES.md).

### v2–v3 — Remember and review
Local vocabulary database, "I already know this" filtering for AI prompts, global search, spaced intervals (1 → 3 → 7 → 14 → 30 days), flashcard review screen.

### Ideas welcome
Open a GitHub issue describing the learning problem a feature would solve, ideally with an image that currently gives a poor result.
