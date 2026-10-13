"""Vocabulary extraction, deduplication and export helpers.

This module never mutates OCR text. It creates a separate learning representation so
Complete/Raw OCR remains the source of truth.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from typing import Iterable

PAIR_RE = re.compile(r"^\s*[-*]\s*\*{0,2}(.+?)\*{0,2}\s+[—–-]\s+(.+?)\s*$")


def norm(value: str) -> str:
    return " ".join(str(value or "").split()).casefold()


@dataclass
class VocabularyEntry:
    source: str
    translation: str = ""
    notes: str = ""
    language: str = ""
    image: str = ""
    status: str = "new"
    tags: tuple[str, ...] = ()

    @property
    def key(self) -> tuple[str, str]:
        return norm(self.source), norm(self.translation)


def extract_pairs(text: str) -> list[tuple[str, str]]:
    """Extract bilingual Markdown bullets without dropping non-matching lines."""
    out = []
    for line in str(text or "").splitlines():
        m = PAIR_RE.match(line)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip()))
    return out


def from_records(records: Iterable[tuple[str, str]], language: str = "", image: str = "") -> list[VocabularyEntry]:
    out, seen = [], set()
    for source, translation in records:
        entry = VocabularyEntry(str(source).strip(), str(translation).strip(), language=language, image=image)
        if entry.source and entry.key not in seen:
            seen.add(entry.key)
            out.append(entry)
    return out


def merge(entries: Iterable[VocabularyEntry], incoming: Iterable[VocabularyEntry]) -> list[VocabularyEntry]:
    """Stable, deterministic duplicate suppression."""
    out, seen = [], set()
    for entry in list(entries) + list(incoming):
        if entry.key in seen:
            continue
        seen.add(entry.key)
        out.append(entry)
    return out


def stats(entries: Iterable[VocabularyEntry]) -> dict[str, int]:
    rows = list(entries)
    return {
        "total": len(rows),
        "new": sum(e.status == "new" for e in rows),
        "known": sum(e.status == "known" for e in rows),
        "difficult": sum(e.status == "difficult" for e in rows),
    }


def to_json(entries: Iterable[VocabularyEntry]) -> str:
    return json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2)


def to_csv(entries: Iterable[VocabularyEntry]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["source", "translation", "notes", "language", "image", "status", "tags"])
    for e in entries:
        writer.writerow([e.source, e.translation, e.notes, e.language, e.image, e.status, ",".join(e.tags)])
    return out.getvalue()


def to_anki(entries: Iterable[VocabularyEntry]) -> str:
    """Tab-separated Anki import format: Front, Back, Tags."""
    return "\n".join(
        f"{e.source}\t{e.translation or e.notes}\t{' '.join(e.tags)}".rstrip()
        for e in entries
    )
