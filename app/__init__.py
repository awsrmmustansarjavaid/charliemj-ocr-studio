"""Charlie MJ OCR & Language Studio - application package (v1.2).

Modules (read in this order to understand the program):
    config      - settings file (config.json), paths and constants
    layout      - pure-Python structure detection: OCR words + positions -> table / title / text
                  (also builds the Markdown notes and reads vocabulary pairs back)
    ocr_engine  - Tesseract wrapper: words WITH positions, full-text Raw mode, per-cell re-reading
    richtext    - document model of the editor (Block / Run) and the exporters (MD, TXT, HTML, DOCX)
    editor      - RichEditor: the formatted text editor panel (panel 4)
    selector    - the "Select Area" tool (drag a box on the picture)
    prompts     - instructions for the optional local AI (buttons + AI Smart mode)
    local_ai    - optional local AI through Ollama (localhost only)
    ui          - the main window: four resizable panels, queue, OCR cards, worker threads
"""
__version__ = "1.2.0"
