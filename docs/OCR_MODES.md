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

## Accuracy levels (Smart and AI Smart)

Under the mode switch, **Accuracy** decides how hard the program works to read **every** cell of a grid:

| Level | What it does | Use it when |
|-------|--------------|-------------|
| **Fast** | first pass only | a quick look; the text is large and clear |
| **Balanced** *(default)* | first pass + **every grid cell re-read on its own** (finds missing and cut-off cells, rows and columns) | normal flashcards and posters |
| **Deep** | Balanced + each cell is also read with the single-language model (fixes `ş ı ğ ç`); if cells are still doubtful or unreadable the picture is **read again at a larger scale** and the more complete result wins | small text, crowded cards, "something is missing" |

### Coverage check

After Smart OCR the status bar reports what was found, for example
`Bilingual table · Turkish → English · 12 pairs (4×3 grid) · confidence 93% · all cells read`.
If something is doubtful you see `⚠ 1 cell(s) unreadable` or `⚠ 2 doubtful – try Deep OCR` instead of a silent gap.

### Raw is the complete capture

**Raw** never discards text: it combines sparse-text OCR with page-analysis OCR, keeps every word either found,
and fixes accent-only differences (`kislik` → `kışlık`) with the Turkish-only model. Smart and AI Smart organise the
text; they never replace it — the original is always one click away (**↻ Raw**, **Copy Original OCR**).

### AI Smart never loses words

The AI writes the title, headings and bullets, but afterwards the program compares the AI notes with the OCR table.
Any OCR pair the AI left out is added under **More vocabulary (from OCR)**, and the status bar says how many.

## ✂ Select Area

Draw boxes on a picture to read only that part. By default the text is **added to the same image** (it stays
*Image N* and uses no batch slot). The tool has zoom, fit, pan, rotate and crop.
→ Full guide: **[Select Area Tool](SELECT_AREA.md)**
