# Select Area Tool

[← Back to main README](../README.md) · Related: [OCR Modes](OCR_MODES.md) · [Text Editor](EDITOR.md) · [Changelog](CHANGELOG.md)

Use **✂ Select Area** when only part of a picture matters, when a crowded layout confuses Smart OCR, or when you want
to add more text to an image you have already read. Open it from the **preview panel** (or double-click the preview),
or from the **✂ Area** button on any result card.

## What happens to the text you select

Choose where the result goes with the three options at the top of the tool:

| Option | Result |
|--------|--------|
| **This image** *(default)* | The box is OCR'd and the text is **added to the image you opened the tool from**. It appears as **✂ Area 1, Area 2 …** under that image's card in panel 3 and as an **Area n** sub-heading under *Image N* in the editor. It does **not** use a slot of the batch limit. |
| **New image** | The box becomes a new image right after the source (named `<file> · area n`) with its own card. This one counts against the batch limit. |
| **Crop the image instead** | The picture itself is cropped to the box. Press **⚡ Process All** or **↻** on the card to read the cropped picture. |

Areas are read in the **current OCR mode and accuracy level** (Smart, Raw or AI Smart; Fast, Balanced or Deep).
Every area keeps its own **Copy**, **⇄ Swap** and **🗑 Remove** buttons, and you can draw as many boxes as you like — the
tool stays open and numbers them 1, 2, 3 … in green.

## The toolbar

| Control | What it does |
|---------|--------------|
| **−  +** | zoom out / in (also keys `-` and `+`) |
| **Fit** | the whole picture fits the window — **the default view** (never enlarged above 100 %) |
| **Fit width** | the picture's width fills the window; scroll down a tall screenshot |
| **100%** | one picture pixel = one screen pixel (key `1`) |
| **⟲  ⟳** | rotate left / right |
| **↶ Undo edit** | undo the last crop or rotation |
| **Clear marks** | remove the green boxes from the screen (the OCR results stay) |
| **Done** | close the tool (or press `Esc`) |

## Mouse and keyboard

| Action | How |
|--------|-----|
| Select a box | drag with the **left** mouse button |
| Zoom at the pointer | `Ctrl` + mouse wheel |
| Scroll | mouse wheel (with `Shift`: sideways) · scroll bars · arrow keys |
| Pan | drag with the **right** or **middle** mouse button |
| Fit / 100 % | `0` / `1` |

## Why it is fast now

* Only the **visible part** of the picture is cut out and scaled, so huge screenshots zoom and pan instantly.
* The boxes are stored in **original-picture pixels**: zooming never moves them, and the OCR always reads the
  **full-resolution original**, never the zoomed preview.
* The result cards are updated one card at a time instead of redrawing every image.

## Tips

* Select **tightly around the text**. For one row or column of a grid, select that row or column.
* A tall phone screenshot: press **Fit width**, scroll to the part you want, then select.
* Selected a wrong box? Nothing is lost: remove the area with its **🗑** button.
* Reached the batch limit? Areas sent to **This image** never count; only **New image** does.

[Back to the OCR Modes guide →](OCR_MODES.md)
