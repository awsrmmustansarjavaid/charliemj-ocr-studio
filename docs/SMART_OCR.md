# Smart OCR — How Messy Pictures Become Clean Tables

[← Back to main README](../README.md) · See also: [OCR Modes](OCR_MODES.md) · [Architecture](ARCHITECTURE.md)

Plain OCR returns one long string and **loses the relationship between words** — the Turkish label and the English
text under it end up far apart. Smart OCR keeps every word's **position** and rebuilds that relationship with
deterministic geometry (no AI, nothing invented). It lives in `app/layout.py` and is unit-tested without a GUI.

## Pipeline
```mermaid
flowchart LR
    A["Image"] --> B["Prepare<br/>gray · invert dark · contrast · 2× upscale"]
    B --> C["Tesseract --psm 11<br/>words + boxes + confidence"]
    C --> D["Segments<br/>lines split at wide gaps"]
    D --> E["Noise filter<br/>UI text · watermark · symbols"]
    E --> F["Pairs<br/>vertical or horizontal"]
    F --> G["Consistency<br/>drop captions / footers"]
    G --> H["Orient<br/>which side is the learned language"]
    H --> I["Bands + heading"]
    I --> J["Re-read cells<br/>language specific"]
    J --> K["Fill missing cells"]
    K --> L["Table + Other text"]
```

## Steps in detail
1. **Prepare** — grayscale; invert light-on-dark screenshots; auto-contrast; upscale small images (phone text is tiny).
2. **Words with boxes** — sparse mode (`--psm 11`) finds scattered labels that normal page analysis skips.
3. **Segments** — words on one line are split wherever the gap is wider than ~1.1× the text height. This separates
   the columns of a card grid, which normal OCR glues into one line.
4. **Noise filter** — drops low-confidence fragments, symbol-only text, oversized shaky text (watermarks) and
   phone / social chrome (`Posts`, `20 hours ago`, `more`, counters).
5. **Pairs** — *vertical* (label with its translation directly **below**; similar text size; same column) or
   *horizontal* (a line with exactly two blocks = a two-column table). The method that finds more pairs wins.
6. **Consistency** — a pair that is unusually wide (a caption line) or low-confidence **and** lines up with no other
   pair (left / centre / right edge) is rejected → captions and footers can no longer become table rows.
7. **Orientation** — Arabic script decides for Urdu / Arabic / Persian; for Turkish its special letters; ties follow
   the majority position (upper / left = original). **⇄ Swap** fixes the rest.
8. **Bands + heading** — pairs are grouped into rows. A pair is the **heading** only if it is *alone in the first
   row*, clearly bigger than the labels and confident — a watermark or a big word inside the grid cannot be a title.
   A standalone big line right above the table is also accepted (with its subtitle).
9. **Re-read cells** — each cell is cropped and read again with the single-language model (`tur` for the original,
   `eng` for the translation), which is better for `ş ı ğ ç`. A new reading is **rejected** if it lost letters or
   changed the word (a photo edge once turned `güzellik beni` into `bea`).
10. **Fill missing cells** — the grid is inferred from the cells that were found (column centres, row pitch). Every
    empty position — and any whole row missing between two found rows — is cropped, enlarged and read as a
    two-line block. This recovered `çil / freckle`, which the first pass had skipped.
11. **Output** — an aligned Markdown table, the heading, and an *Other text* line for everything that is left.

## Result on the test poster
`tests/make_poster.py` builds a replica of a typical Instagram vocabulary post (3×5 photo grid, watermark, phone
header, caption). Smart OCR returns **12 of 12 pairs correct**, no title (there is none), no caption rows.
Raw mode finds every word. These checks run in `tests/test_ocr_integration.py`.

## Known limits
* Pairing is geometric: crowded or decorative layouts can need **⇄ Swap**, **✂ Select Area** or a manual edit.
* Tesseract can struggle with stylised fonts and some Arabic-script text; try Raw or AI Smart.
* Real photos are harder than the test replica; accuracy depends on resolution — use full-size screenshots.

## Tuning
Settings → *Ignore OCR text below this confidence* (default 45). Lower it if real text disappears; raise it if junk appears.

## Complete grid reading (v1.3)

Flashcards are usually a **grid**: a picture, a bold label and a small translation under it, repeated 3 × 4 times.
The first OCR pass can lose cells there (labels almost touch their neighbours, a watermark crosses the picture, a
whole row is missed). Version 1.3 therefore treats a grid as a **lattice** and reads it cell by cell:

1. **Find the lattice.** The cells found by the first pass give the column centres and the row spacing. The column
   spacing is fitted by weighted least squares, so one wrongly read cell cannot shift the far columns. A column in
   which nothing was found is added when it lies next to a known column and inside the picture.
2. **Snap the cell borders.** Each border is moved into the **widest empty gap** between two labels (never into the
   space between two words of one label).
3. **Read every cell on its own.** The crop is deliberately *wider* than the cell and read in sparse mode; then only
   the words whose **centre** lies inside the cell are kept. No letter is cut off and no text of the neighbour leaks in.
   The clean cell reading **replaces** the first reading (it only keeps the old text when the cell gives fewer than two lines).
4. **Recover missing rows.** Rows between, above and below the found rows are read too. A row *above or below* the
   table is accepted only when at least half of its columns read as *label + translation*, so phone-interface text
   (user names, captions) can never become a row.
5. **Deep OCR** additionally reads each cell with the single-language models and lets the readings vote, and retries
   doubtful pictures at a larger scale.
6. **Re-read the heading** (title + subtitle) as one clean block, then add it to the vocabulary list: a card with 12
   pictures and a title gives **13 phrases**. (Setting: *Also list the picture's title as a vocabulary item*.)
7. **Tidy.** If almost every translation starts with a small letter, a stray capital (`Sports`) is lowercased.
8. **Report coverage** in the status bar (grid size, unreadable and doubtful cells).

The result is tested on a generated flashcard with tightly packed labels, a watermark and phone-interface text:
`tests/test_ocr_integration.py` expects **all 12 cells, the title, the subtitle and a 3 × 4 grid** — see [Testing](TESTING.md).
