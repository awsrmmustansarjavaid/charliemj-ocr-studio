"""Charlie MJ OCR & Language Studio - application package (v2.0).

The v2 release preserves the existing OCR/layout foundation and adds lossless
OCR-truth reconciliation, selector selection history, and regression coverage.

Modules:
    config      - portable settings and constants
    layout      - OCR word geometry -> table/title/text plus Markdown notes
    ocr_engine  - Tesseract wrapper and RAW/deep OCR passes
    v2_truth    - immutable OCR observations and coverage safeguards
    richtext    - document model and exporters
    editor      - rich text editor
    selector    - zoom/pan/crop and multi-area selection with undo/redo
    local_ai    - optional localhost Ollama integration
    ui          - main application window and OCR queue
"""
__version__ = "2.0.0"
