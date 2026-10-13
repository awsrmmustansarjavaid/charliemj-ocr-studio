"""Offline personal dictionary and translation-memory store."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict


def _norm(s: str) -> str:
    return " ".join(str(s or "").split()).casefold()


@dataclass
class DictionaryEntry:
    source: str
    translation: str = ""
    notes: str = ""
    language: str = ""
    tags: tuple[str, ...] = ()


class Dictionary:
    def __init__(self, path: str):
        self.path = path
        self.entries: dict[str, DictionaryEntry] = {}
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                rows = json.load(f)
            self.entries = {
                _norm(r["source"]): DictionaryEntry(r["source"], r.get("translation", ""), r.get("notes", ""), r.get("language", ""), tuple(r.get("tags", ())))
                for r in rows if isinstance(r, dict) and r.get("source")
            }
        except (OSError, ValueError, KeyError):
            self.entries = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.entries.values()], f, ensure_ascii=False, indent=2)

    def put(self, entry: DictionaryEntry) -> None:
        self.entries[_norm(entry.source)] = entry
        self.save()

    def lookup(self, source: str) -> DictionaryEntry | None:
        return self.entries.get(_norm(source))

    def remember_translation(self, source: str, translation: str, language: str = "") -> None:
        old = self.lookup(source)
        self.put(DictionaryEntry(source, translation, old.notes if old else "", language or (old.language if old else ""), old.tags if old else ()))

    def values(self) -> list[DictionaryEntry]:
        return list(self.entries.values())
