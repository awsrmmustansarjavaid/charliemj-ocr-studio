# User Guide

[← Back to main README](../README.md) · Previous: [Installation](INSTALLATION.md) · Next: [AI Guide](AI_GUIDE.md)

## Window layout

```text
┌────────────────┬──────────────────┬────────────────────────────────────┐
│ 📥 INPUT       │ 🖼 PREVIEW       │ Formatting: Title H1 H2 H3 • 1. B I │
│ Add / Shot /   │                  │ AI: Learn This · Clean · Translate… │
│ Paste / Folder │   selected image │ ┌────────────────────────────────┐ │
│ Batch: 7 / 20  │                  │ │  Notes editor (Markdown)       │ │
│ [image cards]  │ [Extract][AI OCR]│ └────────────────────────────────┘ │
│ Remove · Undo  │ [Settings]       │ Copy … Clear Save Export           │
│ [Process All]  │                  │                                    │
├────────────────┴──────────────────┴────────────────────────────────────┤
│ ✓ Ready | OCR: Local | AI: Optional                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

## First-time setup
1. Open **⚙ Settings**.
2. Choose your **learning language** (this selects the OCR language) and **your language** (for translations).
3. Pick your **level** and **batch limit**.
4. *(Optional)* paste your Gemini API key. Click **Save Settings**.

## Quick workflows

### A. Fastest: image → text → copy
1. **📸 Screenshot**, drag around the text.
2. Click **🔍 Extract Text**.
3. Click **Copy All** (or select a part and **Copy Selected**).

### B. Many flashcards at once
1. **＋ Add Images** (select many) or **📂 Add Folder**.
2. Click **⚡ Process All**.
3. Watch the cards change to ✓ Done; all text appears in the editor under `## filename` headings.
4. Tidy with the formatting buttons, then **Export**.

### C. Full learning mode (needs API key)
1. OCR your image(s).
2. Click **✨ Learn This**. You get a title, cleaned text, translation, vocabulary and a grammar note.
3. Highlight a difficult word and click **Explain**.
4. Click **Flashcards**, then **Export CSV** and import into Anki.

## Managing the queue

| Action | How |
|--------|-----|
| Preview an image | Click its card |
| Remove some | Tick the checkboxes → **🗑 Selected** (with none ticked it removes the previewed image) |
| Remove everything | **🗑 All** (asks to confirm) |
| Wrong removal | **↶ Undo** restores the last removal |
| Hit the limit | Remove an image, process the batch, or raise the limit in Settings |

## Formatting the notes

Click in a line, then press a button; the button replaces any previous prefix on that line.

| Button | Result |
|--------|--------|
| Title | `# text` |
| H1 / H2 / H3 | `## text` / `### text` / `#### text` |
| • Bullet | `- text` |
| 1. List | `1. text` |
| B / I | Wraps the selection in `**bold**` / `*italic*` |
| ― Line | Inserts `---` |
| ↶ ↷ | Undo / redo |

Example — messy OCR `merhaba nasilsin` becomes:

```markdown
# Turkish Greetings
## Common phrases
- **Merhaba** — Hello
- **Nasılsın?** — How are you?
```

## Copy buttons

| Button | Copies |
|--------|--------|
| Copy Selected | Highlighted text |
| Copy All | Everything (Markdown) |
| Copy Plain | Everything without `#`, `**` markers |
| Copy Original OCR | Raw OCR text only |

## Export

**Save** writes `.md`; **Export TXT** writes plain text; **Export CSV** writes `Front,Back` rows from `- **word** — meaning` lines, skipping duplicates. CSV opens correctly in Excel with Turkish, Urdu and Arabic letters.

## Tips for better OCR
- Crop to just the text; remove buttons, logos and backgrounds.
- Use high-resolution screenshots.
- Choose the correct language in Settings before processing.
- For stylised fonts, try **🤖 AI OCR**, then **Clean**.
- Review AI output — it can make mistakes.

## Privacy
OCR stays on your PC. Text is sent to Google **only** when you click an AI button (or AI OCR sends the image). Your API key is stored in `config.json` beside the app — never share that file.
