# Security & Antivirus Notes

[← Main README](../README.md) · Previous: [User Guide](USER_GUIDE.md) · Next: [Testing](TESTING.md)

You asked for a program that is lightweight, safe, and not flagged by Windows. This page explains what the app does, what it never does, why antivirus sometimes still complains, and what to do about it. **No one can honestly promise zero false positives for an unsigned, self-built `.exe`** — but you can reduce the risk a lot, and you can remove it completely by running from source.

## What the app does — and never does

| The app… | |
|----------|---|
| Reads | only the images you add (file dialog, paste, screenshot you drag) |
| Writes | only `config.json` beside the app and files you export |
| Network | **only** `127.0.0.1` / `localhost` (your own Ollama). Any other address is refused in code (`app/local_ai.py`) |
| Never | sends data to the internet, collects telemetry, auto-updates, downloads or runs code |
| Never | needs administrator rights, writes to the registry, adds a startup entry, installs a service |
| Never | records keystrokes or uses global hotkeys (the screenshot tool only works while you use it) |
| Secrets | none stored — the old cloud API key no longer exists |

The whole program is a few hundred lines of readable Python in `app/` — you can audit it.

## Why antivirus may flag a PyInstaller app anyway

PyInstaller wraps Python in a small launcher (the "bootloader"). The same launcher is used by many programs — including some malware — so some engines flag it on **heuristics**, especially when the file is **new, unsigned, and has no reputation**. These are *false positives*; they say nothing about this code.

## What this repository already does to reduce false positives

| Measure | Where |
|---------|-------|
| One-**folder** build (not one-file self-extracting) | `build.bat`, workflow |
| **No UPX compression** (a classic trigger) | `--noupx` |
| Real **publisher/product metadata** in the `.exe` | `version_info.txt` |
| **Pinned** dependency versions (no surprise updates) | `requirements.txt` |
| Transparent **cloud build** from the public source | `.github/workflows/build.yml` |
| Tests run before the build | workflow / `build.bat` |
| **Microsoft Defender scan** of the result inside the build | workflow step *Defender scan* |
| **SHA-256 checksums** of every file | `SHA256SUMS.txt` in the download |
| No suspicious capabilities (no keylogger, hooks, persistence, remote access) | by design |

## What you can do

1. **Safest of all — run from source:** `pip install -r requirements.txt` then `python main.py`. Nothing is packaged, so there is nothing for antivirus to mis-flag.
2. **Build it yourself** (Option A or B in [Installation](INSTALLATION.md)). A file you built from source you can read is far more trustworthy than one from a stranger.
3. **Verify the download:** compare the hashes in `SHA256SUMS.txt` (PowerShell: `Get-FileHash .\CharlieMJ-OCR.exe -Algorithm SHA256`).
4. **Check with VirusTotal** (virustotal.com). One or two obscure engines flagging a PyInstaller app is common; many detections from well-known vendors would be worth investigating.
5. **If Windows Defender deletes it:** open *Windows Security → Protection history → Restore*, then submit the file as a false positive at <https://www.microsoft.com/en-us/wdsi/filesubmission>. Only add a folder exclusion for a build **you made yourself**.
6. **Code signing (best long-term fix):** a signed `.exe` gets much better treatment from SmartScreen and antivirus. Options: a commercial code-signing certificate, or the free programme for open-source projects from the SignPath Foundation (check their eligibility rules). Signing is not set up in this repository.
7. **Download only from your own repository's Actions artifacts** — never from copies shared by others.

## Ollama (local AI)

- Install only from <https://ollama.com>. It is a separate program and is not bundled here, so the model files never touch this app's `.exe`.
- By default Ollama listens on your own PC only. Do not expose it to the network; the app will refuse non-local addresses anyway.

## Dependencies

Only three runtime packages (customtkinter, pillow, pytesseract), pinned to tested versions. Update them deliberately and re-run the tests. Tesseract comes from the Chocolatey/UB Mannheim builds and language data from the official `tessdata_fast` repository.

## Reporting a problem

If you find a security issue, please open a GitHub issue (or contact the maintainer privately if you prefer) with steps to reproduce. Do not post API keys, personal images, or private text.
