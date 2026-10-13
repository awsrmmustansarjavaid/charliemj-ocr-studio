# AI Guide — Local Ollama

[← Main README](../README.md) · Previous: [User Guide](USER_GUIDE.md) · Next: [Roadmap](ROADMAP.md)

AI is an **optional local layer**. OCR, Smart/Raw modes, Select Area, the editor and exports work without it. The app uses Ollama on your own PC; it does not use a cloud AI API.

## Setup

1. Install Ollama from [ollama.com](https://ollama.com).
2. Start Ollama and install a model, for example `ollama pull gemma3:4b`.
3. In Charlie MJ open **Settings → Test AI connection**.
4. Select the installed model in Settings if needed.

The default endpoint is `http://127.0.0.1:11434`. The application rejects non-local AI endpoints.

## AI Smart

**AI Smart** first performs Smart OCR. It then gives the local model the picture and OCR text and asks for:

- a main title;
- section headings and optional subheadings;
- one bilingual vocabulary bullet per visible item;
- no invented vocabulary and no ignored OCR items.

The OCR result remains the source of truth. After the AI response, the application performs a deterministic lossless merge and appends any OCR pairs the model omitted under `## More vocabulary (from OCR)`.

If a vision model cannot accept the image, the app retries with OCR text. If local AI is unavailable, the Smart OCR result is kept instead of leaving the image empty.

## Local AI Agents

The **Local AI Agents** panel provides three local roles:

| Agent | Purpose |
|---|---|
| **OCR Structure** | Structure the complete OCR and picture into titles, sections and vocabulary pairs. |
| **Vocabulary** | Extract every supplied bilingual pair without capping the count. |
| **Study Tutor** | Explain and teach from the supplied OCR text without inventing vocabulary. |

## Editor AI actions

The editor can run **Learn This, Clean, Table, Translate, Explain, Vocabulary,** and **Flashcards** on the selection or on the whole document when nothing is selected.

- **Clean** and **Table** replace the selected content.
- The other actions append their answer.
- AI output is ordinary editable text and should always be reviewed.

## Privacy

Images and OCR text stay on the local machine during OCR. Optional AI requests go only to the configured localhost Ollama server. Installing an additional Tesseract language pack is a separate, user-requested download from the official Tesseract tessdata source.

## Troubleshooting

| Problem | Action |
|---|---|
| Ollama unavailable | Start Ollama and press **Test AI connection** again. |
| Model missing | Run `ollama pull <model>` and select it in Settings. |
| Vision error | Use a vision-capable model or let AI Smart fall back to OCR text. |
| Slow responses | Use a smaller local model or use Smart/Raw OCR without AI. |
| Non-local endpoint rejected | Use `http://127.0.0.1:11434`. |

See [Local AI](LOCAL_AI.md) for the operational guide and [Security](SECURITY.md) for the privacy model.
