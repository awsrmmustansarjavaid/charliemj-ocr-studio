# User Guide

[← Main README](../README.md) · Previous: [Installation](INSTALLATION.md) · Next: [Testing](TESTING.md)

## The four panels

```text
1 INPUT        → images, folder, paste, screenshot, queue and Process All
2 PREVIEW      → image, Smart/Raw/AI Smart, Fast/Balanced/Deep, Extract, Select Area, Settings
3 OCR RESULTS  → Image N cards, editable OCR, Copy, Smart, Raw, AI, Swap, Area, Delete
4 TEXT EDITOR  → notes, formatting, Find/Replace, cleanup, AI actions and export
```

## First use

1. Open **Settings** and choose the learning language and translation language.
2. Add images or paste/capture a screenshot.
3. Choose an OCR mode and accuracy level.
4. Run **Extract Text** for one image or **Process All** for the queue.
5. Review the result card and the automatically populated editor.

## Recommended workflows

### Complete flashcard set

1. Add the full image set. The application queue is not capped by the old batch-limit setting.
2. Choose **Smart + Balanced** for normal use.
3. Process all images.
4. Check the pair/grid coverage shown by the status bar.
5. Use **Deep** on difficult screenshots and **Raw** when you need to see every OCR word.
6. Edit/export the final notes.

### Dense screenshot

Use **Balanced** first. The program can perform a targeted 3× structural recovery when the initial OCR has many lines but fails to identify a reliable bilingual structure. Use Select Area if only a region is problematic.

### AI study notes

Choose **AI Smart**. Smart OCR runs first, then local Ollama produces titles, headings and vocabulary. Any OCR pairs omitted by the model are added under **More vocabulary (from OCR)**.

### Exact OCR capture

Choose **Raw**. It is intentionally less filtered than Smart and is the best source for comparing what Tesseract saw.

## Queue management

Images can be reordered, removed, restored with Undo and processed again. The same OCR job path is used whether you click a card's Smart/Raw/AI button or Process All.

## Result cards

Each Image N card has editable text. **Swap** reverses bilingual table columns. **Area** opens the selector for focused OCR. **Copy Original OCR** preserves the Raw source for comparison.

## Select Area

Use zoom, fit, fit-width, 100%, pan, rotate and crop. Draw multiple boxes. By default an area is attached to its source Image N; it can also become a new image.

See [Select Area](SELECT_AREA.md).

## Editor

The editor derives notes from OCR results until you edit it. It supports formatting, lists, alignment, Find/Replace, Sort A–Z, duplicate removal, Focus mode and Restore. Export to MD, TXT, HTML, DOCX or CSV.

See [Text Editor](EDITOR.md).

## Languages

The portable bundle starts with English, Turkish, Urdu, Arabic and Persian. Installed Tesseract packs are discovered dynamically, and additional official packs can be installed on demand.

## Privacy

OCR is local. Optional AI uses local Ollama. A requested language-pack installation is the only normal path that downloads language data from the internet.
