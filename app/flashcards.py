"""Lightweight flashcards with offline spaced repetition.

The scheduler is intentionally deterministic and dependency-free. It stores dates and
intervals in the card object, so projects remain portable.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Iterable


@dataclass
class Flashcard:
    front: str
    back: str
    tags: tuple[str, ...] = ()
    due: str = ""
    interval: int = 0
    ease: float = 2.5
    repetitions: int = 0
    lapses: int = 0

    def review(self, quality: int, today: date | None = None) -> "Flashcard":
        """Apply a compact SM-2-style review rating (0..5)."""
        quality = max(0, min(5, int(quality)))
        today = today or date.today()
        if quality < 3:
            self.lapses += 1
            self.repetitions = 0
            self.interval = 1
            self.ease = max(1.3, self.ease - 0.2)
        else:
            self.repetitions += 1
            if self.repetitions == 1:
                self.interval = 1
            elif self.repetitions == 2:
                self.interval = 6
            else:
                self.interval = max(1, round(self.interval * self.ease * (0.8 + quality / 10)))
            self.ease = max(1.3, self.ease + 0.1 - (5 - quality) * 0.08)
        self.due = (today + timedelta(days=self.interval)).isoformat()
        return self


def from_vocabulary(entries: Iterable[object]) -> list[Flashcard]:
    cards = []
    for entry in entries:
        front = str(getattr(entry, "source", "")).strip()
        back = str(getattr(entry, "translation", "")).strip()
        if front:
            cards.append(Flashcard(front, back, tuple(getattr(entry, "tags", ()))))
    return cards


def due_cards(cards: Iterable[Flashcard], today: date | None = None) -> list[Flashcard]:
    today = today or date.today()
    return [c for c in cards if not c.due or c.due <= today.isoformat()]


def to_json(cards: Iterable[Flashcard]) -> str:
    return json.dumps([asdict(c) for c in cards], ensure_ascii=False, indent=2)


def to_tsv(cards: Iterable[Flashcard]) -> str:
    return "\n".join(f"{c.front}\t{c.back}\t{' '.join(c.tags)}".rstrip() for c in cards)


def to_csv(cards: Iterable[Flashcard]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["front", "back", "tags", "due", "interval", "ease", "repetitions", "lapses"])
    for c in cards:
        writer.writerow([c.front, c.back, " ".join(c.tags), c.due, c.interval, c.ease, c.repetitions, c.lapses])
    return out.getvalue()
