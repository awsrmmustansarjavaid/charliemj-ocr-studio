# Local AI Guide (Ollama)

[← Main README](../README.md) · Previous: [Smart OCR](SMART_OCR.md) · Next: [Technologies](TECHNOLOGIES.md)

## Why local?

- **Private:** your text and images never leave your PC. The app refuses any address that is not `localhost` / `127.0.0.1`.
- **No account, no API key, no cost, no quota.**
- **Optional:** OCR, tables, copy and export work without any AI.

AI runs through **[Ollama](https://ollama.com)**, a separate free program. It is *not* bundled, which keeps this app small and avoids antivirus trouble from huge model files.

## Setup (once)

1. Install Ollama from <https://ollama.com> and start it (it runs in the system tray).
2. Open a terminal (`Win` key → type *cmd*) and download a model:
   ```text
   ollama pull gemma3:4b
   ```
3. In the app open **⚙ Settings → 🔌 Test local AI connection**. You should see *Ollama is running · 1 model(s) installed*. Pick the model in the dropdown and **Save Settings**.

The bottom-right of the window shows **AI: Ollama ✓** when it is reachable, or *not running (optional)*.

## Choosing a model

Check <https://ollama.com/library> for current names and sizes.

| Model (example) | Good for | Needs |
|-----------------|----------|-------|
| `gemma3:4b` (default) | Text **and images** (AI OCR); decent multilingual | ~4 GB disk, 8 GB RAM recommended |
| `qwen2.5vl:3b` | Vision-focused alternative | ~3 GB disk, 8 GB RAM |
| `gemma3:1b` | Fast, text only, weak PCs | ~1 GB disk, 4 GB RAM |

A larger model is usually more accurate but slower. The first request after starting loads the model and takes longer.

## What each button does

| Button | Sends | Result |
|--------|-------|--------|
| ✨ Learn This | selected text (or the whole box) | appended: title, translation, vocabulary, grammar note |
| Clean | text | **replaces** it with a tidy version |
| Translate | text | appended translation |
| Explain | word / sentence | meaning, pronunciation, base form, part of speech, examples |
| Vocabulary | text | bullets `- **word** — meaning` |
| Flashcards | text | bullets ready for CSV export |
| 📊 Table | OCR text | rebuilds a `# / language / translation` table from messy text |
| 🤖 AI OCR | the **image** | reads the picture with the vision model |

Click inside a result box first: the toolbar acts on the box you last clicked, on the **selection** if there is one.

## Safety rules built into the prompts
All prompts tell the model to **keep the original words and never invent unclear text**. Still, small models make mistakes — treat AI output as a draft, especially for Urdu, Arabic and Persian.

> **AI OCR vs Smart OCR:** for clean text, Tesseract + Smart OCR is usually *more* accurate and much faster than a small vision model. Use AI OCR as a fallback for difficult images.

## Troubleshooting

| Message | Fix |
|---------|-----|
| *Local AI is not running…* | Start Ollama, then press **Test local AI connection** |
| *Model '…' is not installed* | Run `ollama pull <model>` or choose an installed one in Settings |
| Very slow | Use a smaller model; close other heavy programs; first call loads the model |
| Only local addresses allowed | The Ollama address must be `http://127.0.0.1:11434` (default) |
| Empty or odd AI answer | Select less text, or try another model |

See [Security](SECURITY.md) and [Architecture](ARCHITECTURE.md#7-local-ai).
