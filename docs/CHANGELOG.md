# Changelog

[← Back to main README](../README.md) · See also: [OCR Modes](OCR_MODES.md) · [Text Editor](EDITOR.md)

## v1.2.0 — Three OCR modes, Select Area, Text Editor

### Added
- **Three OCR modes** — **Smart** (structure → table), **Raw** (every word, nothing filtered) and **AI Smart**
  (local AI writes a main title, headings, subheadings and bullet vocabulary). → [OCR Modes](OCR_MODES.md)
- **✂ Select Area tool** — drag a box on the picture; every box becomes its own *Image N* and is OCR'd at once.
- **Panel 4: Text Editor** — the OCR results flow in automatically (*Image N* → main title → headings → bullets) and
  can be formatted (bold, italic, underline, size, colour, highlight, lists, alignment…) and exported to
  MD / TXT / HTML / DOCX / CSV. → [Text Editor](EDITOR.md)
- Four **resizable panels** (drag the dividers) and a **◀ Focus** button that gives the editor the whole window.
- Editor tools: find & replace, sort bullets A–Z, remove duplicate lines, auto-update / restore, zoom (`Ctrl + wheel`).
- Smart OCR **fills missing table cells** (grid inference) and recovers whole missing rows.
- New files: `app/editor.py`, `app/richtext.py`, `app/selector.py`, `app/prompts.py`; new tests (19 in total).

### Fixed (found with real screenshots of vocabulary posters)
| Problem | Cause | Fix |
|---------|-------|-----|
| A watermark fragment became the **title** and swallowed a real row | any big pair anywhere could be the heading | the heading must be **alone in the first row**, clearly bigger, and confident |
| The Instagram **caption** appeared as table rows | caption lines were paired like labels | pairs that are too wide / unaligned / low-confidence are dropped |
| Words **cut short** (`güzellik beni` → `bea`, `çift çene` → `cene`) | the second reading of a cell included a photo edge | readings that lose letters or change the word are rejected |
| **Missing cells** (`çil / freckle`) | the first pass skipped small text next to photos | the grid is inferred and empty cells are re-read |
| **Raw** mode lost words | automatic page analysis dropped scattered labels | two passes combined; nothing filtered |
| `Posts`, `20 hours ago`, `more` polluted the result | phone / social-media chrome | recognised and ignored |

### Changed
- The old *Combined* tab and *AI OCR* button are replaced by the **Text Editor** and the **AI Smart** mode.
- Export buttons moved to the editor (it holds the final, formatted text).
- Version resource (`version_info.txt`) and window title show **1.2.0**.
- CI: the bundled Tesseract no longer contains the training tools (smaller zip, smaller antivirus surface);
  the real-OCR integration test is informational so it can never block a build.

## v1.1.0 — Smart OCR and local AI
Structure detection (card grids, two-column lists), per-image result cards (*Image 1, 2, …*) with break lines,
local AI through Ollama (no cloud), security hardening (pinned dependencies, checksums, Defender scan).

## v1.0.0 — First release
Portable OCR with image queue, batch limit, screenshot / paste / folder input, notes editor, copy and export buttons.
