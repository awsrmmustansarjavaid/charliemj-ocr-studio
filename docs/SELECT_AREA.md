# Select Area Tool

[← Main README](../README.md) · Related: [OCR Modes](OCR_MODES.md) · [Text Editor](EDITOR.md)

Use **✂ Select Area** when only part of a screenshot matters or when a dense region benefits from a focused OCR pass. Open it from the preview panel, double-click the preview, or use **Area** on a result card.

## Area destinations

| Destination | Behaviour |
|---|---|
| **This image** | The OCR result becomes an Area child of the source Image N. It stays grouped with the source image. |
| **New image** | The selected region becomes its own queue item and result card. |
| **Crop** | The source image is cropped; process it again with the normal OCR controls. |

The current OCR mode and accuracy are used. Because the queue runtime is no longer application-capped, creating a new image does not depend on an old batch-limit setting.

## Controls

- **− / +** zoom.
- **Fit** and **Fit width** for large screenshots.
- **100%** for one image pixel per displayed pixel.
- Rotate left/right.
- Crop and undo the last image edit.
- Clear marks without deleting already captured OCR results.
- Draw multiple boxes in one session.

## Mouse and keyboard

- Left-drag: create a selection box.
- `Ctrl` + mouse wheel: zoom around the pointer.
- Mouse wheel / scroll bars: scroll.
- Right or middle drag: pan.
- `0`: Fit.
- `1`: 100%.
- `Esc`: close the selector.

## Why it works well on large screenshots

The selector keeps box coordinates in original-image pixels and renders only the visible viewport. OCR reads the original-resolution crop, not a zoomed preview.

## Tips

Select tightly around the difficult text. For a crowded card grid, selecting one row or one column can make a focused recovery easier. Areas sent to **This image** remain attached to the source card and appear as Area headings in the editor.
