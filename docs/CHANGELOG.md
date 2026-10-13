# Changelog

[← Main README](../README.md) · See also: [OCR Modes](OCR_MODES.md) · [Smart OCR](SMART_OCR.md) · [Testing](TESTING.md)

## v2.3.0 — Unified OCR runtime and dense-screenshot recovery

### Reliability
- Single-image **Smart / Raw / AI Smart** buttons and **Process All** now use the same OCR job manager and result-commit path.
- The queue runtime processes every attached image without an application-imposed queue cap and can reprocess images that already have results.
- OCR jobs report explicit start, result, error and finish states; cancellation is supported.
- Added a Python syntax regression test covering `main.py` and every module in `app/` so malformed packaged imports are caught before freezing.

### OCR completeness
- Smart OCR remains a **complete-image first pass**. Structure is detected after extraction rather than using a vocabulary count as a cap.
- Balanced OCR can recover dense bilingual screenshots with a bounded 3× structural retry when the first pass produces substantial text but is classified as plain text.
- Recovery only accepts a genuine table-sized result, avoiding false structure from random UI text.
- AI Smart keeps OCR as the source of truth and deterministically appends OCR pairs the AI omitted under **More vocabulary (from OCR)**.

### Language support
- Tesseract language discovery is dynamic: installed `.traineddata` packs are detected and made selectable.
- Official `tessdata_fast` packs can be installed on demand into the portable bundle.

### Local AI
- Local Ollama connection diagnostics accept an explicit endpoint for testing.
- Local AI Agents provide **OCR Structure**, **Vocabulary** and **Study Tutor** roles.

### Packaging
- Windows packaging explicitly collects the application package and CustomTkinter submodules.
- CI verifies critical imports, runs the regression suite, starts the frozen EXE for a smoke test, scans the packaged directory with Defender when available, and writes SHA-256 checksums.

## v1.3 and earlier

Earlier releases introduced complete grid reading, Fast/Balanced/Deep accuracy, Select Area, the four-panel editor, Smart/Raw/AI Smart modes, local Ollama integration, exports, portable packaging and the original Smart OCR layout engine.

See the repository history for the detailed v1.x development record.
