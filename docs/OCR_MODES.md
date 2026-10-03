# OCR Modes and the Select Area Tool

[← Back to main README](../README.md) · Previous: [Features](FEATURES.md) · Next: [Text Editor](EDITOR.md)

Panel 2 has a three-way switch. The chosen mode is used by **⚡ Process All**, **🔍 Extract Text**,
**✂ Select Area** and is remembered between sessions. Each result card also has its own **↻ Raw / ↻ Smart / ↻ AI**
buttons, so one image can be re-read in a different mode at any time.

| | **Smart** | **Raw** | **AI Smart** |
|---|---|---|---|
| Goal | clean *Original \| Translation* table | **all** text, exactly as found | title, headings, subheadings, bullet vocabulary |
| Needs internet / AI | no (offline) | no (offline) | local AI (Ollama), still no cloud |
| Speed | ~5 s per image | ~5 s per image | ~5 s + model time (10–120 s) |
| Filters noise | yes (UI text, captions, watermarks) | **no** | yes |
| Best for | vocabulary posters, flashcards, two-column lists | when you want every word, or Smart guessed wrong | polished notes with real headings |
| Risk | a very unusual layout may need **⇄ Swap** | contains junk text too | the model can make mistakes – always check |

## Smart mode
Reads the *layout*, not just the text. In short: word positions → text blocks → pairs (label above translation,
or left | right) → table rows → heading → missing-cell recovery → Markdown table.
Result for a poster with 12 pictures and a Turkish label + English label under each:

```
| #  | Turkish          | English       |
|----|------------------|---------------|
|  1 | gamze            | dimple        |
|  2 | çift çene        | double chin   |
| …  | …                | …             |
```
Phone / social-media text (`Posts`, `20 hours ago`, usernames, captions) is kept out of the table; whatever is
left goes into an **Other text** line under it. Full algorithm: [Smart OCR](SMART_OCR.md).

**⇄ Swap** flips the two columns if the original and the translation were detected the wrong way round.

## Raw mode — the complete text
Raw runs two Tesseract passes (sparse text + automatic page analysis) and keeps **every** word either pass finds.
Text blocks that sit side by side stay on one line, separated by four spaces, so the picture's layout is still visible:

```
gamze    çift çene    gözenek
dimple   double chin  pore
```
Nothing is removed — not even junk such as watermark fragments — so you can decide what matters.
Raw text appears in the editor under a *Raw text* heading.

## AI Smart mode
1. Smart OCR runs first (this is the "ground truth").
2. The picture **and** the OCR text are sent to your local model with strict rules: use exactly this structure,
   include every visible item, never invent items, fix only clear OCR mistakes, ignore interface text.
3. The answer is shown in the result card and in the editor:

```markdown
# Skin Features          → main title      (Heading 1 in the editor)
## Face                  → heading         (Heading 2)
### Marks                → subheading      (Heading 3)
- **gamze** — dimple     → bullet vocabulary: original — English
```
**If the model is not installed or cannot see images**, the app falls back automatically: first to text-only AI
(OCR text without the picture), and if no AI is available at all, to the plain Smart result — with a message in the
status bar. You never end up with an empty result. Setup: [Local AI](LOCAL_AI.md).

## ✂ Select Area
Use it when only part of a picture matters, or when a crowded layout confuses Smart OCR.

1. Click an image in the queue, then **✂ Select Area** (or double-click the preview).
2. A window opens with the full picture (tall screenshots scroll with the mouse wheel).
3. **Drag a box** around the part to read. Release the mouse: the box becomes a new image in the queue,
   directly after the original, named `<file> · area 1`, and is OCR'd immediately in the current mode.
4. Drag more boxes (they are numbered 1, 2, 3…) or press **Esc / Done**.

Every area is a normal *Image N* with its own card, so numbering, reordering, swapping, deleting and exporting all work as usual.
Tips: select **tightly around the text**; for one grid row select the row, not the whole page.
