# Security and Privacy

[← Main README](../README.md) · Previous: [User Guide](USER_GUIDE.md) · Next: [Testing](TESTING.md)

## Local-first processing

- OCR runs on the user's machine with Tesseract.
- Raw images and OCR records are kept in the application process until the user exports them.
- Optional AI uses Ollama on the local machine. The application rejects non-local Ollama endpoints.
- Additional Tesseract language packs may be downloaded only when the user requests them; the source is the official Tesseract tessdata repository.
- There is no cloud OCR API, telemetry service, auto-start entry, registry installation or administrator requirement.

## Portable storage

`config.json` is stored beside the executable. The application does not need a system-wide installation.

## Windows executable safety

The portable EXE is built with PyInstaller in one-folder mode and without UPX. GitHub Actions runs the regression suite before packaging, performs a frozen-EXE startup smoke test, scans the output with Microsoft Defender when the runner supports it, and writes SHA-256 checksums.

An unsigned PyInstaller application can still trigger Windows SmartScreen or antivirus heuristics. A detection should be evaluated against the public source, workflow result and checksum rather than assuming that every alert is meaningful.

## Verify a download

Use the `SHA256SUMS.txt` included with the portable build. In PowerShell:

```powershell
Get-FileHash .\CharlieMJ-OCR.exe -Algorithm SHA256
```

Compare the resulting hash with the corresponding line in the manifest.

## Local AI security

Ollama is separate from the application and its model files are not bundled into the EXE. Keep Ollama bound to the local machine. The app's localhost check prevents the configured AI endpoint from being changed to a remote host through normal settings.

## Dependencies

Runtime Python packages are pinned in `requirements.txt`. Build dependencies are pinned separately in `requirements-build.txt`. Tesseract and its language data are bundled by the Windows workflow.

## Reporting a security issue

Do not post API keys, private images or sensitive OCR text in a public issue. Report reproducible security problems privately to the maintainer when possible.
