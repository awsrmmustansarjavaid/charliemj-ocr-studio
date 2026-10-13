# Testing

[← Main README](../README.md) · Related: [Smart OCR](SMART_OCR.md) · [Architecture](ARCHITECTURE.md)

The project has unit, OCR-integration and UI/build regression coverage.

## Run the complete Python suite

```bash
pip install -r requirements-build.txt
python -m unittest discover -s tests -v
```

The suite covers layout/structure logic, rich-text conversion/export, queue/job integration, local-agent diagnostics, OCR recovery and Python syntax compilation.

## Important regression coverage

- **Complete-image OCR** does not cap extraction from a vocabulary reference count.
- **Dense screenshot recovery** can retry a text-classified image and accept only a genuine structured result.
- **Lossless AI merge** restores OCR pairs that AI formatting omitted.
- **Batch and per-image OCR** use the same job entry point.
- **Already-completed images** can be reprocessed by the unified queue runtime.
- **Local agent status** accepts an explicit endpoint for diagnostics.
- Every `main.py` and `app/*.py` file is compiled by the syntax regression test.

## OCR integration

`tests/test_ocr_integration.py` exercises real Tesseract when it is available. The GitHub workflow treats this integration check as informational while the complete regression suite is blocking.

## Packaged EXE smoke test

The Windows workflow starts `dist\CharlieMJ-OCR\CharlieMJ-OCR.exe` after PyInstaller finishes and requires the frozen process to remain alive through the startup grace period. This catches missing hidden imports and packaging-only failures.

## CI pipeline

1. Install Tesseract.
2. Prepare bundled language data.
3. Install pinned dependencies.
4. Run the complete unittest suite.
5. Run OCR integration checks.
6. Build the portable EXE.
7. Start the frozen EXE as a smoke test.
8. Run Microsoft Defender when available.
9. Generate `SHA256SUMS.txt` and the final ZIP.

## Manual release checklist

- Process a mixed set of screenshots in Smart Balanced mode.
- Compare the result count with the complete visible screenshot, not an expected vocabulary count.
- Re-run a difficult image individually and confirm it uses the same result path as Process All.
- Try Raw and Deep on a difficult image.
- Test Select Area and editor exports.
- Test AI Smart with Ollama running and stopped.
- Verify the packaged EXE starts on a clean Windows environment.
