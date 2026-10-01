# Installation & Building the `.exe`

[← Main README](../README.md) · Previous: [Architecture](ARCHITECTURE.md) · Next: [User Guide](USER_GUIDE.md)

**Option A is easiest** — nothing to install. If antivirus worries you, read [Security](SECURITY.md) first.

## Option A — Build in the cloud with GitHub Actions (recommended)

1. Create a GitHub account and upload this repository (keep the hidden `.github` folder).
2. Open the **Actions** tab → **Build Windows portable EXE** → **Run workflow**.
3. Wait ~5–10 minutes for a green tick. The run installs everything, **runs the tests**, builds without UPX, scans with Microsoft Defender and writes checksums.
4. Open the finished run → **Artifacts** → download **CharlieMJ-OCR-Portable**.
5. Unzip it and run `CharlieMJ-OCR.exe`. Compare `SHA256SUMS.txt` if you want to verify files.

## Option B — Build on your own PC

### Requirements
- Windows 10/11 (64-bit)
- Python 3.11+ from python.org (tick **Add Python to PATH**)
- Tesseract for Windows (UB Mannheim build)

### Steps
1. Install Tesseract. In the project folder create a folder named `tesseract`.
2. Copy everything from `C:\Program Files\Tesseract-OCR` into `tesseract` (the `.exe` and all `.dll` files).
3. Put these files in `tesseract\tessdata` (the small *tessdata_fast* versions are fine): `eng`, `tur`, `urd`, `ara`, `fas` `.traineddata` — from <https://github.com/tesseract-ocr/tessdata_fast>.
4. Double-click **`build.bat`** (installs pinned packages, runs tests, builds, copies Tesseract, writes a checksum).
5. Your app is in `dist\CharlieMJ-OCR\CharlieMJ-OCR.exe`.

Final layout:
```text
CharlieMJ-OCR/
├── CharlieMJ-OCR.exe
├── _internal/            (Python runtime, libraries)
├── tesseract/
│   ├── tesseract.exe
│   └── tessdata/         (*.traineddata)
├── SHA256SUMS.txt
└── config.json           (created when you press Save in Settings)
```

## Option C — Run from source (no `.exe` at all)

```bash
pip install -r requirements.txt
python main.py
```
Without a bundled `tesseract/` folder the app uses a Tesseract installed on your PATH. This is the option with **zero antivirus risk**, because nothing is packaged.

## Optional: local AI

Install **Ollama** and a model — see the [Local AI guide](LOCAL_AI.md). Everything except the AI buttons works without it.

## Making it portable
Copy the **entire** `CharlieMJ-OCR` folder to a USB drive or another PC. Keep the `.exe` inside its folder. (Ollama is separate; the AI buttons need it on that PC.)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| SmartScreen "unknown publisher" | **More info → Run anyway** (the app is not code-signed — see [Security](SECURITY.md)) |
| Antivirus quarantines the `.exe` | Usually a PyInstaller false positive — follow [Security](SECURITY.md) |
| *tesseract is not installed* | `tesseract\tesseract.exe` must sit beside the `.exe` |
| Wrong letters for a language | Check the `.traineddata` file exists and the right language is chosen in Settings |
| Table is wrong or empty | Use a larger/original image, check *Minimum OCR confidence*, try **↻ Raw**, use **⇄ Swap** |
| AI buttons say Ollama is not running | See [Local AI](LOCAL_AI.md#troubleshooting) |
| GitHub build fails | Open the failed run, copy the error text, and report it |
