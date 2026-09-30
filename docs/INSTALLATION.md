# Installation & Building the `.exe`

[← Back to main README](../README.md) · Previous: [Architecture](ARCHITECTURE.md) · Next: [User Guide](USER_GUIDE.md)

There are three ways to get the app. **Option A is easiest** — nothing to install.

## Option A — Build in the cloud with GitHub Actions (recommended)

1. Create a GitHub account and upload this repository (keep the `.github` folder).
2. Open the **Actions** tab → **Build Windows portable EXE** → **Run workflow**.
3. Wait 5–10 minutes for a green tick.
4. Open the finished run, scroll to **Artifacts**, download **CharlieMJ-OCR-Portable**.
5. Unzip it and run `CharlieMJ-OCR.exe`.

The workflow (`.github/workflows/build.yml`) installs Python and Tesseract, downloads the language data, runs PyInstaller, and zips the result.

## Option B — Build on your own PC

### Requirements
- Windows 10/11 (64-bit)
- Python 3.11+ from python.org (tick **Add Python to PATH**)
- Tesseract for Windows (UB Mannheim build)

### Steps
1. Install Tesseract. Inside the project folder create a folder named `tesseract`.
2. Copy everything from `C:\Program Files\Tesseract-OCR\` into `tesseract\` (the `.exe` and all `.dll` files).
3. Put these files in `tesseract\tessdata\` (the small *tessdata_fast* versions are fine):
   `eng.traineddata`, `tur.traineddata`, `urd.traineddata`, `ara.traineddata`, `fas.traineddata`
   — download from <https://github.com/tesseract-ocr/tessdata_fast>.
4. Double-click **`build.bat`**.
5. Your app is in `dist\CharlieMJ-OCR\CharlieMJ-OCR.exe`.

Final folder layout:

```text
CharlieMJ-OCR/
├── CharlieMJ-OCR.exe
├── _internal/            (Python runtime, libraries)
├── tesseract/
│   ├── tesseract.exe
│   └── tessdata/         (*.traineddata)
└── config.json           (created on first Save in Settings)
```

## Option C — Run from source (for development)

```bash
pip install -r requirements.txt
python main.py
```
Without the bundled `tesseract/` folder, the app uses a Tesseract installed on your PATH.

## Getting a Gemini API key (optional)

1. Go to <https://aistudio.google.com> and create an API key (free tier available).
2. In the app open **⚙ Settings** and paste it into **Gemini API key**.
3. Click **Save Settings**.

OCR works without a key; only the AI buttons need it.

## Making it portable

Copy the **entire** `CharlieMJ-OCR` folder to a USB drive or another PC. Keep the `.exe` inside its folder.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Windows SmartScreen warning | Click **More info → Run anyway** (the app is not code-signed) |
| "tesseract is not installed" error | Make sure `tesseract\tesseract.exe` sits next to the `.exe` |
| OCR output is garbage for a language | Check the matching `.traineddata` is in `tesseract\tessdata\` and the right language is chosen in Settings |
| AI buttons say "Add your Gemini API key" | Paste a key in Settings |
| Poor OCR on stylised fonts | Crop tightly, or use **🤖 AI OCR** |
| GitHub build fails | Open the failed run, copy the error text, and open an issue |
| Antivirus flags the `.exe` | Common with PyInstaller apps; build it yourself from source to verify |
