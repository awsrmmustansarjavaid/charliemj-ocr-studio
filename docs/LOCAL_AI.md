# Local AI (Ollama)

[← Back to main README](../README.md) · Previous: [OCR Modes](OCR_MODES.md) · See also: [Security](SECURITY.md)

AI is **optional**. OCR, Smart / Raw modes, the editor and all exports work without it. When you do want it, the
model runs **on your own PC** through [Ollama](https://ollama.com): no cloud, no account, no API key. The app talks
to Ollama only on `localhost` — any other address is refused by the code (`app/local_ai.py`).

## Setup (once)
1. Install Ollama from <https://ollama.com> and let it run in the background.
2. Open a terminal and run `ollama pull gemma3:4b` (about 3 GB; it can read pictures and writes decent Turkish).
3. In the app: **⚙ Settings → Test AI connection**. You should see *✓ Ollama is running*. The status bar then
   shows `AI: ✓ gemma3:4b`.

| Your PC | Suggested model |
|---------|-----------------|
| 8 GB RAM, no GPU | `gemma3:4b` (slow but works) or `gemma3:1b` (text only, fast) |
| 16 GB RAM / a GPU | `gemma3:4b` or a larger vision model |

The model name is free text in Settings — use any model you have installed (`ollama list`).

## Where the AI is used
| Place | What it does |
|-------|--------------|
| **AI Smart** mode | Smart OCR first, then picture + OCR text → main title, headings, subheadings, bullet vocabulary |
| Editor **✨ Learn This** | notes: title, cleaned text, translation, vocabulary, grammar note |
| **Clean** | fixes OCR mistakes only, keeps the structure (replaces the selection) |
| **📊 Table** | turns messy text into `- **word** — meaning` bullets (replaces the selection) |
| **Translate / Explain / Vocabulary / Flashcards** | add an answer at the end |

Editor buttons work on the **selected lines**, or on the whole editor if nothing is selected.

## Safety rules built into every prompt
* "Do not invent words that are not in the text; if unclear, keep it as written."
* AI Smart receives the **OCR text as ground truth** and must include every visible item, copy words exactly and
  ignore social-media interface text.
* Answers are inserted as ordinary editable text — always double-check them.

## Automatic fallbacks (AI Smart)
1. The model cannot see images → the request is repeated **text-only** with the OCR text.
2. Ollama is not running / the model is missing → the **Smart result** is shown instead, with the reason in the status bar.

## Troubleshooting
| Message | Fix |
|---------|-----|
| *Ollama is not running* | start Ollama (it normally starts with Windows) |
| *Model 'x' is not installed* | `ollama pull x`, or choose an installed model in Settings |
| Very slow | use a smaller model; close other programs; AI Smart takes a while per image on CPU |
| Poor Turkish / Urdu answers | try another model; use Smart (no AI) and edit by hand |
| *Only a local Ollama address is allowed* | use `http://127.0.0.1:11434` |

## Adding your own AI button
Open `app/prompts.py` and add an entry to `ACTIONS`:
```python
"Examples": (lambda t: ctx() + "Write 3 simple example sentences for: " + t, "append"),
```
`"append"` adds the answer at the end; `"replace"` replaces the selected lines. The button appears automatically.

## AI Smart safety net (v1.3)
A local model can skip an item. After every AI Smart answer the program compares the AI bullets with the Smart OCR
table (names are compared at ≥ 80 % similarity, so a corrected letter does not count as missing) and appends any
missing pair under **More vocabulary (from OCR)**. The status bar tells you how many items were added.
The picture's title/subtitle counts too when *Also list the picture's title as a vocabulary item* is on.
