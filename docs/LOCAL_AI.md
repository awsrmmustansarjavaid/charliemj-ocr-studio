# Local AI (Ollama)

[← Main README](../README.md) · Previous: [OCR Modes](OCR_MODES.md) · See also: [AI Guide](AI_GUIDE.md)

Ollama is optional. Smart OCR, Raw OCR, Select Area, the result cards, editor and exports work without it.

## Setup

1. Install Ollama from [ollama.com](https://ollama.com).
2. Pull a local model, for example `ollama pull gemma3:4b`.
3. Open **Settings → Test AI connection** in Charlie MJ.
4. Select the model you installed.

The normal endpoint is `http://127.0.0.1:11434`. The application allows local Ollama endpoints only.

## AI Smart

AI Smart runs Smart OCR first, then sends the image plus complete OCR text to the local model. The requested output is a main title, section headings, optional subheadings and bilingual vocabulary bullets. The model is told not to invent items or ignore visible vocabulary.

After the model returns, OCR pairs are compared with the AI result. Any missing OCR pair is appended under `## More vocabulary (from OCR)` so AI formatting cannot silently reduce the extracted vocabulary.

If the model cannot accept images, the app retries with OCR text. If Ollama is unavailable, the Smart OCR result remains available.

## Local AI Agents

The **Local AI Agents** window provides:

- **OCR Structure** — structure complete OCR plus the picture.
- **Vocabulary** — extract every supplied bilingual pair without an entry cap.
- **Study Tutor** — explain supplied OCR for the learner's level.

## Editor AI buttons

The editor provides **Learn This, Clean, Table, Translate, Explain, Vocabulary** and **Flashcards**. Actions operate on selected text or the full editor when there is no selection.

## Reliability and privacy

AI output is always editable and should be reviewed. Images and OCR are not sent to a cloud AI provider by this application. The only AI service is the user's local Ollama instance.

## Troubleshooting

| Message | Fix |
|---|---|
| Ollama unavailable | Start Ollama and press **Check/Test AI connection** again. |
| Model missing | Pull the model with `ollama pull <model>`. |
| Vision not supported | Use a vision model or rely on the OCR-text fallback. |
| Very slow | Use a smaller model or process without AI. |
