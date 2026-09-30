# Project Overview

[← Back to main README](../README.md) · Next: [Features](FEATURES.md)

## What is this program?

**Charlie MJ OCR & Language Studio** is a lightweight, portable Windows desktop application. It extracts text from pictures — flashcards, screenshots, subtitles, textbook pages — and turns that text into clean, structured study notes with titles, headings and bullet lists. Notes can be copied or exported in one click, and an optional AI layer (Google Gemini) can clean, translate, explain and convert the text into vocabulary and flashcards.

It ships as a **folder with one `.exe`**. There is no installer: copy the folder to your Desktop or a USB drive and run it.

## Why was it built?

The author is learning several languages (Turkish, Urdu, Arabic, Persian, English) and downloads many flashcard images. The original workflow looked like this:

1. Look at a flashcard image.
2. **Type every word by hand** into a notes document, or paste the image into Gemini and copy the answer back.
3. Format the notes manually (titles, headings, bullets).
4. Repeat for every card.

That is slow and discourages studying. The goal of this project is to remove the typing so the learner can **focus on learning, not data entry**.

## Goals

| Goal | How it is met |
|------|---------------|
| Remove manual typing | Screenshot / paste / add images → automatic OCR |
| Produce tidy notes | Markdown-style editor with title, H1–H3, bullets, numbering |
| Easy copying | Separate buttons: Copy Selected, Copy All, Copy Plain, Copy Original OCR |
| Handle many images | Batch queue with a configurable limit (default 20) and Process All |
| Fix mistakes easily | Remove Selected, Remove All, Undo Remove |
| Save learning time | Optional AI: Learn This, Clean, Translate, Explain, Vocabulary, Flashcards |
| Stay lightweight | Python + Tkinter + Tesseract; no local AI models, no Electron |
| Stay portable | One folder, config saved beside the `.exe`, no installer or admin rights |

## Non-goals (for v1)

- Not a full spaced-repetition system (planned — see [Roadmap](ROADMAP.md)).
- Not a cloud service: there is no account, server or database.
- Not a replacement for a dedicated dictionary; AI answers should be double-checked.

## Who is it for?

Language learners, students and anyone who regularly needs to turn images of text into editable, organised notes without installing heavy software.

## Design principles

1. **Local first** – OCR works fully offline.
2. **AI is optional** – it only runs when you click, on the text you select, so you control quota and privacy.
3. **Every step is optional** – you can just do *Screenshot → OCR → Copy*, or use the full *Learn This* flow.
4. **Simple UI** – primary actions always visible, nothing buried in menus.
5. **Portable** – no registry entries, no installer, settings live next to the app.

## Related documents

- [Features](FEATURES.md) · [Technologies](TECHNOLOGIES.md) · [Architecture](ARCHITECTURE.md)
- [Installation](INSTALLATION.md) · [User Guide](USER_GUIDE.md) · [AI Guide](AI_GUIDE.md) · [Roadmap](ROADMAP.md)
