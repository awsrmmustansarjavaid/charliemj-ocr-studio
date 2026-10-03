# Text Editor (Panel 4)

[← Back to main README](../README.md) · Previous: [OCR Modes](OCR_MODES.md) · Next: [Technologies](TECHNOLOGIES.md)

The editor is where the OCR results become **finished study notes**. It fills itself automatically — you only
polish and export.

## What appears automatically
For every processed image, in queue order:

```
Image 1                      ← Title style (the image number, updates on delete / reorder)
Screenshot_2026….jpg         ← small grey file name
ELDİVEN ÇEŞİTLERİ            ← Heading 1  (main title found in the picture / by AI)
Types of Gloves              ← Heading 3  (subtitle)
Vocabulary                   ← Heading 2
• kışlık eldiven — winter gloves     ← bullets, original in bold
• muayene eldiveni — medical gloves
──────────────────────────  ← separator line
Image 2 …
```
* **Smart** → title, *Vocabulary* heading, bullets. **Raw** → *Raw text* heading + paragraphs.
  **AI Smart** → the model's title / headings / subheadings / bullets.
* The editor is rebuilt after every OCR run, delete, move, swap — **until you edit it yourself**.

## Your edits are protected
| State | Meaning |
|-------|---------|
| *Auto-update* ✔ and not edited | the editor follows the OCR results live |
| You typed or formatted something | the editor is marked **✎ edited by you**; OCR updates no longer overwrite it |
| **⟳ Update from OCR** | rebuilds the editor (asks first if you have edits) |
| **⤺ Restore** | brings back the text that the last update replaced |

## Toolbar reference
| Row | Controls |
|-----|----------|
| 1 | **Style** (Normal, Title, Heading 1–3) · **B** bold · **I** italic · **U** underline · **S** strike · **A−** / size / **A+** |
| 2 | **• List** · **1. List** · align left / centre / right · **🎨 Color** · **― Line** · **Clear fmt** · **🖍 Highlight** (yellow, green, pink, blue) |
| 3 | undo / redo · **🔍 Find** · **Sort A–Z** · **No duplicates** · **⟳ Update from OCR** · **⤺ Restore** |
| 4 | AI buttons: ✨ Learn This · Clean · 📊 Table · Translate · Explain · Vocabulary · Flashcards — and, on the right, the **Auto-update** switch and the **◀ Focus** button |

Formatting applies to the **selection**; with no selection it applies to the **word under the cursor**
(or the whole line for sizes and colours).

### Lists that behave
* **Enter** on a bullet starts the next bullet; on a numbered line it starts the next number.
* **Enter** on an empty bullet ends the list.
* Select several lines and press **• List** / **1. List** to convert them; press again to remove it.

### Advanced tools
* **Find & Replace** (`Ctrl+F`): match case, find next, replace, replace all.
* **Sort A–Z**: sorts every bullet list alphabetically (formatting is kept).
* **No duplicates**: removes repeated lines (same text, ignoring case) — handy when several cards share a word.
* **Zoom**: `Ctrl + mouse wheel`.
* **◀ Focus**: hides panels 1–3 so the editor fills the window; click again to bring them back.
* **Resize panels**: drag the thin dividers between panels.
* **Counters**: words, lines and bullets are shown above the text.

### Shortcuts
`Ctrl+B` bold · `Ctrl+I` italic · `Ctrl+U` underline · `Ctrl+F` find · `Ctrl+Z / Ctrl+Y` undo / redo · `Ctrl+A` select all · `Ctrl + wheel` zoom

## AI buttons
They act on the **selected lines**, or on the **whole editor** if nothing is selected. *Clean* and *Table* replace the
text; the others add their answer at the end. Needs the local AI — see [Local AI](LOCAL_AI.md).

## Copy and export
| Button | Result |
|--------|--------|
| Copy All / Copy Selected / Copy Markdown | clipboard |
| **Save .md** | Markdown (`# Image 1`, `## main title`, `### heading`, `- **word** — meaning`) |
| **TXT** | plain text with bullets |
| **HTML** | a styled web page (bold, colours, sizes, bullet lists) |
| **DOCX** | a Word document with the formatting (no extra software needed to create it) |
| **CSV** | `Image, Original, Translation` from the vocabulary bullets, duplicates removed — import into Anki / Excel |

All files are UTF-8, so Turkish, Urdu, Arabic and Persian letters stay intact.

## Limits
* Bullets and numbers are text prefixes, so in Word they are typed characters rather than Word list objects.
* No pictures or tables inside the editor (vocabulary tables become bullets).
* The Windows clipboard receives plain text, not formatted text; use HTML or DOCX export to keep formatting.
