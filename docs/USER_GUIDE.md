# User Guide

[← Main README](../README.md) · Previous: [Installation](INSTALLATION.md) · Next: [Security](SECURITY.md)

## Window layout

```text
┌────────────────┬──────────────────┬──────────────────────────────────────┐
│ 📥 INPUT       │ 🖼 PREVIEW       │ Formatting: Title H1 H2 H3 • 1. B I   │
│ Add / Shot /   │                  │ Local AI: Learn This · Clean · Table… │
│ Paste / Folder │  selected image  │ [Results] [Combined]                  │
│ Batch: 7 / 20  │                  │  Image 1  [Copy][↻ Smart][↻ Raw][⇄][🗑]│
│ 1. card ▲▼     │ OCR mode         │  ┌ Turkish | English table ┐          │
│ 2. card ▲▼     │ (Smart | Raw)    │  ──────────────────────────           │
│ Remove · Undo  │ [Extract][AI OCR]│  Image 2 …                            │
│ [Process All]  │ [Settings]       │ Copy … Combine · Save · Export        │
├────────────────┴──────────────────┴──────────────────────────────────────┤
│ ✓ Ready                                    OCR: Local | AI: Ollama ✓      │
└───────────────────────────────────────────────────────────────────────────┘
```

## First-time setup
1. **⚙ Settings** → choose your **learning language** (selects the OCR model and the first table column) and **your language** (second column, translations).
2. Optionally set level, batch limit, theme, and the *Minimum OCR confidence* (default 45).
3. *(Optional)* install Ollama and press **🔌 Test local AI connection** — see [Local AI](LOCAL_AI.md).
4. **Save Settings**.

## Workflows

### A. Fastest — one picture to a table
1. **📸 Screenshot** and drag around the flashcard (or **📋 Paste Image**, or **＋ Add Images**).
2. Choose **Smart** and press **🔍 Extract Text**.
3. **Copy** on the card.

### B. A batch of up to 20 flashcards
1. **＋ Add Images** (select many) or **📂 Add Folder**.
2. **⚡ Process All** — watch the statuses and the progress text.
3. Each image now has its own card: **Image 1, Image 2, …** with a line between them.
4. Fix anything inside the boxes (they are editable), use **⇄ Swap** if columns are reversed.
5. **🧩 Combine All OCR** to see everything in one document, or **Export**.

### C. Study mode with local AI
1. In a card box, select a word or sentence (or select nothing to use the whole box).
2. Press **Explain**, **Translate**, **Vocabulary**, **Flashcards**, **✨ Learn This** …
3. **Export CSV** → import into Anki.

## The queue

| Action | How |
|--------|-----|
| Preview an image | Click its card |
| Reorder | **▲ ▼** on the card — the **Image N** numbers update by themselves |
| Remove some | Tick checkboxes → **🗑 Selected** (none ticked = the previewed image), or **🗑** on a result card |
| Remove all | **🗑 All** (asks first) |
| Mistake | **↶ Undo** puts the images back **at their old positions** |
| Limit reached | Remove an image, process the batch, or raise the limit in Settings |

## Result cards

| Part | Meaning |
|------|---------|
| **Image N** | Position in the queue (renumbers automatically) |
| Thumbnail, file name, status | Which picture and whether it is done |
| **Copy** | Copies this image's result |
| **↻ Smart / ↻ Raw** | Re-run OCR on this image in that mode |
| **⇄ Swap** | Swap the language columns of a table |
| **🗑** | Remove this image |
| Text box | Editable; the horizontal line below separates images |

## Formatting buttons (act on the box you last clicked)

| Button | Result |
|--------|--------|
| Title / H1 / H2 / H3 | `###` / `##` / `###` / `####` before the line |
| • Bullet / 1. List | `- text` / `1. text` |
| B / I | wraps the selection in `**bold**` / `*italic*` |
| ― Line | inserts `---` |
| ↶ ↷ | undo / redo |

## Copy and export

| Button | Copies / writes |
|--------|-----------------|
| Copy Selected | the highlighted text |
| Copy All | all images: `## Image N`, file name, text, `---` between images |
| Copy Plain | same without Markdown symbols / table pipes |
| Copy Original OCR | untouched OCR text of every image |
| Save (.md), Export TXT | the combined document |
| Export CSV | `Image, <language>, <translation>`, duplicates removed (also reads your manual edits and AI bullets) |

CSV opens correctly in Excel with Turkish, Urdu and Arabic letters.

## Tips for better results
- Use the **original** picture, not a screenshot of a screenshot. Bigger text = better OCR.
- Crop away apps, menus and comments before OCR.
- Pick the correct learning language **before** processing.
- If a table looks wrong, press **↻ Raw** to see what OCR found, then adjust *Minimum OCR confidence*.
- Treat AI output as a draft and double-check new words.

## Privacy
OCR and AI run on your PC. The app talks only to a local Ollama address and has no telemetry. See [Security](SECURITY.md).
