# Installation and Windows Build

[← Main README](../README.md) · Previous: [Architecture](ARCHITECTURE.md) · Next: [User Guide](USER_GUIDE.md)

## Use the verified Windows build

The repository's **Downloads** section points to the verified portable build produced by GitHub Actions. Download the ZIP, extract it, and run `CharlieMJ-OCR.exe`.

The build contains the application, bundled Tesseract and language data, plus `SHA256SUMS.txt`.

## Build with GitHub Actions

1. Keep the `.github` directory when cloning or uploading the repository.
2. Open **Actions → Build Windows portable EXE**.
3. Run the workflow or push to `main`.
4. Wait for the Windows build to finish its tests, packaging and startup smoke test.
5. Download the `charliemj-ocr-studio-v2-final` artifact.

The workflow currently uses Python 3.11 and bundles English, Turkish, Urdu, Arabic and Persian Tesseract data. The application can later install additional official language packs on demand.

## Build locally on Windows

Requirements:

- Windows 10/11 64-bit.
- Python 3.11.
- Tesseract for Windows.

From the repository root:

```powershell
pip install -r requirements-build.txt
.\build.bat
```

The portable output is created under `dist\CharlieMJ-OCR\` and includes the EXE, bundled Tesseract and a SHA-256 manifest.

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

If Tesseract is not bundled, the app can use a Tesseract installation available on the system PATH.

## Optional local AI

Install Ollama separately and pull a local model such as `gemma3:4b`. OCR does not require Ollama.

## Portable behaviour

Settings are stored as `config.json` beside the EXE. Copy the whole `CharlieMJ-OCR` directory to another Windows PC or USB drive to keep the application portable.

## Troubleshooting

| Problem | Action |
|---|---|
| EXE closes immediately | Use the latest green workflow artifact; the workflow includes a packaged-EXE startup smoke test. |
| Tesseract missing | Verify `tesseract\tesseract.exe` is beside the EXE. |
| Language missing | Install the required official Tesseract `.traineddata` pack and select it in Settings. |
| Smart table is incomplete | Use Balanced/Deep, inspect the coverage status, or use Raw/Select Area for a difficult region. |
| AI unavailable | Start Ollama or continue with Smart/Raw OCR. |
| SmartScreen warning | The portable EXE is not code-signed; verify its SHA-256 checksum and source before running. |
