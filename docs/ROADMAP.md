# Roadmap

[← Back to main README](../README.md) · Previous: [AI Guide](AI_GUIDE.md) · Start: [Overview](PROJECT_OVERVIEW.md)

## Status

| Version | Theme | Status |
|---------|-------|--------|
| **v1** | Core OCR, queue, notes editor, copy/export, Gemini AI, settings | ✅ Done |
| v1.1 | Drag-and-drop, global hotkey `Ctrl+Shift+O`, crop before OCR, OCR language auto-detect | 📝 Planned |
| v2 | Vocabulary library (Know / Learning / Review), duplicate detection across sessions, search | 📝 Planned |
| v3 | Flashcard review with spaced repetition; Anki `.apkg` export | 📝 Planned |
| v4 | Text-to-speech, pronunciation practice | 💡 Idea |
| v5 | Progress dashboard, projects per language, PDF/video-subtitle capture, optional RapidOCR engine | 💡 Idea |

## Details

### v1.1 — Faster capture
- **Drag & drop** images into the window (`tkinterdnd2`).
- **Global hotkey** to capture → OCR → append without opening the app.
- **Crop / select area** on an already added image.
- **Image enhancement** toggle (denoise, deskew).

### v2 — Vocabulary library
- Persist words in a local SQLite file beside the app.
- Status per word: ✓ Know · ⭐ Learning · 🔄 Review · ✕ Ignore.
- AI skips words already marked *Know*.
- Global search across notes and vocabulary.

### v3 — Review
- Spaced intervals: 1 → 3 → 7 → 14 → 30 days.
- Flashcard screen (front / reveal / Again · I Know).

### v4–v5 — Enjoyment features
Pronunciation practice, streaks and daily goals, per-language projects, multi-language comparison, PDF OCR.

## Contributing ideas
Open a GitHub issue describing the feature and the language-learning problem it solves.
