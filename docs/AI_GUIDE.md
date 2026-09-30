# AI Guide

[← Back to main README](../README.md) · Previous: [User Guide](USER_GUIDE.md) · Next: [Roadmap](ROADMAP.md)

## How AI is used

AI is an **optional layer** on top of local OCR. It never runs automatically. Each button sends your **selected text** (or all notes if nothing is selected) to Google Gemini and puts the answer back in the editor.

## Setup
1. Create a key at <https://aistudio.google.com>.
2. **⚙ Settings → Gemini API key** → paste → **Save Settings**.
3. Optionally change **Gemini model** (default `gemini-2.5-flash`).

## Buttons

| Button | Sends | Result placement |
|--------|-------|------------------|
| ✨ Learn This | text | appended: title, cleaned text, translation, vocabulary, grammar |
| Clean | text | **replaces** selection/notes with a tidy Markdown version |
| Translate | text | appended translation in your language |
| Explain | word/sentence | appended: meaning, pronunciation, base form, part of speech, 2 examples |
| Vocabulary | text | appended bullet list of useful words for your level |
| Flashcards | text | appended `- **front** — back` bullets |
| 🤖 AI OCR | the **image** | appended extracted text |

## Personalisation
Every prompt starts with a learner profile built from Settings:
`The learner is studying <language>, native language <your language>, level <level>.`
A lower level makes the AI choose simpler, more useful vocabulary.

## Strict vocabulary format
Vocabulary and flashcards are requested as `- **word** — meaning`. The CSV exporter reads exactly this shape, so keep it when editing by hand.

## Adding your own AI action
Open `main.py`, find the `ACTIONS` dictionary and add an entry:

```python
"Examples": (lambda t: ctx() + "Write 3 simple example sentences for: " + t, "append"),
```
Use `"append"` to add below the notes or `"replace"` to swap the selection. A new button appears automatically.

## Privacy, cost and reliability
- Sent data: only the text/image you choose.
- The free tier has rate limits; if you see an error in the status bar, wait and retry.
- AI can be wrong — especially for rare words, Urdu/Arabic/Persian diacritics and idioms. Verify important items.
- Your key lives in `config.json`; it is excluded by `.gitignore`.

[Architecture: AI integration](ARCHITECTURE.md#7-ai-integration)
