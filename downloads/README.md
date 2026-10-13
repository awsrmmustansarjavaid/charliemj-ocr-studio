# Downloads

The main README download button points to the current portable build stored in this directory.

## Current verified build

**[Download CharlieMJ OCR & Language Studio v2.3.0](./CharlieMJ-OCR-Portable-v2.3.0.zip)**

This ZIP is the `charliemj-ocr-studio-v2-final.zip` produced by GitHub Actions run **38412578017** from commit `a379a22ba2f80ae585cc074b32f8ba43d13338c3`.

Original workflow artifact page: https://github.com/awsrmmustansarjavaid/charliemj-ocr-studio/actions/runs/38412578017/artifacts/11823197425

The build includes the portable EXE, bundled Tesseract, language data and `SHA256SUMS.txt`.

## Verification

After extraction, compare the executable hashes with `SHA256SUMS.txt` using PowerShell:

```powershell
Get-FileHash .\CharlieMJ-OCR.exe -Algorithm SHA256
```

For build provenance and the full CI process, see [Installation](../docs/INSTALLATION.md) and [Security](../docs/SECURITY.md).
