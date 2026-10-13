"""Small persistent correction history used by OCR/editor workflows."""
from __future__ import annotations

import json
import os
import time
from typing import Any


class History:
    def __init__(self, path: str, limit: int = 100):
        self.path, self.limit = path, max(1, int(limit))
        self.entries: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            self.entries = data if isinstance(data, list) else []
        except (OSError, ValueError):
            self.entries = []

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.entries[-self.limit:], f, ensure_ascii=False, indent=2)

    def record(self, before: str, after: str, reason: str = "edit") -> None:
        if before == after:
            return
        self.entries.append({"time": time.time(), "before": before, "after": after, "reason": reason})
        self._save()

    def undo(self, current: str) -> str | None:
        """Return the previous value when current matches the last recorded result."""
        if not self.entries:
            return None
        last = self.entries[-1]
        if last.get("after") != current:
            return None
        self.entries.pop()
        self._save()
        return last.get("before")

    def clear(self) -> None:
        self.entries = []
        try:
            os.remove(self.path)
        except OSError:
            pass
