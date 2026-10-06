# Roadmap

[← Back to main README](../README.md) · See also: [Changelog](CHANGELOG.md) · [Project Overview](PROJECT_OVERVIEW.md)

Guiding rule: **never destroy information during OCR** — Raw (complete) → Smart (organised) → AI Smart (polished);
every later layer can go back to the complete original.

| Version | Theme | Status |
|---------|-------|--------|
| v1.0 – v1.1 | Core OCR, queue, notes, Smart OCR, local AI | ✅ done |
| v1.2 | 3 OCR modes, Select Area, Text Editor, missing-cell recovery | ✅ done |
| **v1.3** | **Complete flashcards (grid reading, Deep OCR, coverage check), Select Area 2.0 (zoom / fit / crop / rotate, results added to the same image), faster UI** | ✅ **done** |
| v1.4 | **Review & correct**: Original / Smart / AI tabs per image, confidence marks (✓ ⚠ ?), click a doubtful word to correct it, remembered corrections, save / open a project file, drag-and-drop files, global hotkey capture | 📝 planned |
| v1.5 | **Vocabulary layer**: vocabulary inbox (choose what to save), duplicate and *already learned* detection across images, personal dictionary (local file), base form / part of speech / example sentence through the local AI, **Anki export** (TSV / package) | 📝 planned |
| v2.0 | **Study**: flashcards from OCR (vocabulary, sentence, cloze, image cards), review mode with simple spaced repetition, daily words and progress | 💡 idea |

## Ideas under consideration
* **Maximum accuracy** level and an *Advanced settings* page (segmentation, pre-processing switches), with a *Simple mode* for beginners.
* A common **OCR engine interface** so another engine can be tried later without touching the window.
* Per-stage **progress** ("Pass 1 → cell reading → merging → AI formatting") instead of a single bar.
* Undo / redo across the whole application (selections, deletions, AI changes).
* **Smart Language Capture**: one button that captures, reads, pairs, checks duplicates and fills the editor.

## How features are chosen
Does it help a learner turn a picture into correct, complete study material with the least typing? Everything else waits.
Open a GitHub issue with the learning problem you want solved.
