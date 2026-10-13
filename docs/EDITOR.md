# Text Editor (Panel 4)

[← Main README](../README.md) · Previous: [OCR Modes](OCR_MODES.md) · Next: [Technologies](TECHNOLOGIES.md)

Panel 4 turns OCR results into editable study notes. It updates automatically while the document is still under application control; once you edit the document, your edits are protected from automatic OCR refreshes.

## Automatic structure

For each queue image the editor can show:

```text
Image 1
file-name.png
Main title
Heading / section
Vocabulary
• original — translation

Image 2
...
```

- **Smart** results become title + vocabulary notes.
- **Raw** results become a Raw text section.
- **AI Smart** preserves the model's title, headings, subheadings and bullets.
- Captured **Area 1, Area 2, ...** results remain under their source image.

## Formatting

The editor supports title/heading styles, bold, italic, underline, strike, font size, text colour, highlights, bullets, numbered lists, alignment and separator lines.

## Editing tools

- Find and replace.
- Sort vocabulary lists A–Z.
- Remove duplicate lines.
- Undo/redo.
- Auto-update from OCR with **Restore** for the previous editor state.
- **Focus** mode hides the first three panels.
- `Ctrl` + mouse wheel changes editor zoom.
- `Ctrl+B`, `Ctrl+I`, `Ctrl+U`, `Ctrl+F`, `Ctrl+Z`, `Ctrl+Y`, `Ctrl+A` are supported where applicable.

## Local AI actions

**Learn This, Clean, Table, Translate, Explain, Vocabulary,** and **Flashcards** use the configured local Ollama model. They work on selected text or on the whole editor when no selection exists.

## Copy and export

Panel 3 provides Copy Selected, Copy All, Copy Plain and Copy Original OCR. The editor exports:

- Markdown (`.md`)
- plain text (`.txt`)
- HTML (`.html`)
- Word (`.docx`)
- CSV vocabulary pairs (`.csv`)

CSV extraction uses the standard `- **original** — translation` vocabulary shape. Unicode text such as Turkish, Urdu, Arabic and Persian remains UTF-8.

## Captured areas

A Select Area capture sent to **This image** is represented as an Area child of the source image. Removing an area removes it from both the result card and the derived editor notes.

The editor is a presentation layer over OCR records; it does not replace the stored OCR source. This keeps Raw OCR available for comparison and correction.
