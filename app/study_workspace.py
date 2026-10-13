"""High-level OCR-to-learning workspace facade.

Keeps learning data separate from OCR records so AI/corrections can never delete source OCR.
"""
from __future__ import annotations

from . import flashcards, vocabulary
from .dictionary import Dictionary, DictionaryEntry


class StudyWorkspace:
    def __init__(self, dictionary: Dictionary | None = None):
        self.dictionary = dictionary
        self.vocabulary: list[vocabulary.VocabularyEntry] = []
        self.flashcards: list[flashcards.Flashcard] = []

    def ingest_markdown(self, text: str, language: str = "", image: str = "") -> int:
        incoming = vocabulary.from_records(vocabulary.extract_pairs(text), language, image)
        before = len(self.vocabulary)
        self.vocabulary = vocabulary.merge(self.vocabulary, incoming)
        return len(self.vocabulary) - before

    def ingest_pairs(self, pairs, language: str = "", image: str = "") -> int:
        incoming = vocabulary.from_records(pairs, language, image)
        before = len(self.vocabulary)
        self.vocabulary = vocabulary.merge(self.vocabulary, incoming)
        return len(self.vocabulary) - before

    def make_flashcards(self) -> int:
        existing = {(c.front.casefold(), c.back.casefold()) for c in self.flashcards}
        added = 0
        for card in flashcards.from_vocabulary(self.vocabulary):
            key = (card.front.casefold(), card.back.casefold())
            if key not in existing:
                existing.add(key)
                self.flashcards.append(card)
                added += 1
        return added

    def remember(self, source: str, translation: str, language: str = "") -> None:
        if self.dictionary:
            self.dictionary.remember_translation(source, translation, language)

    def lookup(self, source: str):
        return self.dictionary.lookup(source) if self.dictionary else None

    def enrich_from_dictionary(self) -> int:
        if not self.dictionary:
            return 0
        changed = 0
        for entry in self.vocabulary:
            saved = self.dictionary.lookup(entry.source)
            if saved and saved.translation and not entry.translation:
                entry.translation = saved.translation
                changed += 1
        return changed

    def statistics(self) -> dict[str, int]:
        return vocabulary.stats(self.vocabulary)
