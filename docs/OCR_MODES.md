# OCR Modes

[← Main README](../README.md) · Previous: [Features](FEATURES.md) · Next: [Text Editor](EDITOR.md)

All OCR entry points use the same job manager. **Process All**, **Extract Text**, and each result-card **Smart / Raw / AI** button reach the same worker/result pipeline.

| Mode | Purpose | AI required |
|---|---|---|
| **Smart** | Complete screenshot OCR → structure detection → bilingual tables, titles and recovered cells. | No |
| **Raw** | Complete OCR text with no Smart layout filtering. | No |
| **AI Smart** | Smart OCR + local AI notes with an OCR lossless safety net. | Optional Ollama |

## Smart OCR

1. OCR the whole image and keep word positions/confidence.
2. Detect lines, blocks, pairs, headings and grid geometry.
3. Re-read grid cells when the selected accuracy level calls for it.
4. Recover missing cells/rows conservatively.
5. Return a structured Markdown result plus coverage information.

A dense screenshot that initially looks like plain text can receive one bounded 3× structural recovery pass in Balanced mode. The recovery is accepted only when it produces a real table-sized bilingual result.

The OCR pass is **not capped by the number of vocabulary items expected by a user or by the AI output**. Extraction happens first; structure and deduplication happen afterwards.

## Raw OCR

Raw is the comparison path when you want everything the OCR engine saw. It is intentionally less filtered than Smart and may include captions, interface text or watermark fragments.

Use **Copy Original OCR** to preserve or compare this source text.

## AI Smart

AI Smart first runs Smart OCR. It sends the picture and OCR text to the local Ollama model, requesting:

```markdown
# Main title
## Heading
### Subheading
- **original phrase** — translation
```

Afterwards, the program compares the AI output with the OCR pairs. Missing pairs are appended under **More vocabulary (from OCR)**.

If vision is unavailable, the model is retried with OCR text. If AI is unavailable, the Smart result remains visible.

## Accuracy

| Level | Behaviour |
|---|---|
| **Fast** | First OCR pass only. |
| **Balanced** | Cell-aware reading plus targeted dense-screenshot recovery. |
| **Deep** | Balanced processing plus language-specific voting and larger-scale retry for difficult cells. |

The status bar reports the detected structure, pair count, grid information and confidence/coverage warnings where available.

## Select Area

Select Area uses the current mode and accuracy. Captures can be attached to the source image or turned into a separate image record. See [Select Area](SELECT_AREA.md).
