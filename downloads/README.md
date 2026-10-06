# CharlieMJ-OCR-Portable

This folder is where the **download button** in the main [README](../README.md) points:
`CharlieMJ-OCR-Portable/CharlieMJ-OCR-Portable.zip`.

The `.exe` cannot be built from the source files alone — it is produced on a Windows machine:

1. Open the **Actions** tab of this repository → **Build Windows portable EXE** → **Run workflow**.
2. When the run is green, download the artifact **CharlieMJ-OCR-Portable** (a `.zip`).
3. Put that file in this folder under the name **`CharlieMJ-OCR-Portable.zip`** and commit it.

> ⚠️ GitHub rejects single files larger than **100 MB** in a normal commit (and 25 MB when uploading in the
> browser). If your zip is bigger, attach it to a **Release** instead (Releases → *Draft a new release* → upload
> the zip) and point the README button to the release asset.

Verify any download with the `SHA256SUMS.txt` that is inside the zip — see [docs/SECURITY.md](../docs/SECURITY.md).
