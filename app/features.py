"""Public feature facade for the v2.1 learning workspace.

The GUI can import this module without pulling optional OCR engines or network libraries.
"""
from .dictionary import Dictionary, DictionaryEntry
from .flashcards import Flashcard, due_cards, from_vocabulary
from .history import History
from .ocr_manager import EngineAdapter, EngineInfo, OCREngineManager, default_manager
from .project_store import load_project, save_project
from .study_workspace import StudyWorkspace
from .vocabulary import VocabularyEntry, extract_pairs, from_records, merge, stats, to_anki, to_csv, to_json

__all__ = [
    "Dictionary", "DictionaryEntry", "Flashcard", "due_cards", "from_vocabulary", "History",
    "EngineAdapter", "EngineInfo", "OCREngineManager", "default_manager", "load_project", "save_project",
    "StudyWorkspace", "VocabularyEntry", "extract_pairs", "from_records", "merge", "stats", "to_anki", "to_csv", "to_json",
]
