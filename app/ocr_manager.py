"""Lazy OCR engine registry.

Tesseract remains the built-in/default engine. Alternative engines can be registered by
an adapter without adding their heavyweight dependencies to the portable build.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class EngineInfo:
    name: str
    description: str
    optional: bool = True


@dataclass
class EngineAdapter:
    info: EngineInfo
    available: Callable[[], bool]
    recognize: Callable[..., Any]


class OCREngineManager:
    def __init__(self):
        self._engines: dict[str, EngineAdapter] = {}

    def register(self, adapter: EngineAdapter) -> None:
        self._engines[adapter.info.name] = adapter

    def names(self) -> list[str]:
        return list(self._engines)

    def status(self) -> list[dict[str, Any]]:
        result = []
        for name, adapter in self._engines.items():
            try:
                available = bool(adapter.available())
                error = ""
            except Exception as exc:
                available, error = False, str(exc)
            result.append({"name": name, "available": available, "optional": adapter.info.optional, "description": adapter.info.description, "error": error})
        return result

    def recognize(self, name: str, image, **kwargs):
        adapter = self._engines[name]
        if not adapter.available():
            raise RuntimeError(f"OCR engine '{name}' is not available")
        return adapter.recognize(image, **kwargs)

    def benchmark(self, image, names: list[str] | None = None, **kwargs) -> list[dict[str, Any]]:
        rows = []
        for name in names or self.names():
            adapter = self._engines.get(name)
            if not adapter:
                continue
            try:
                if not adapter.available():
                    continue
                started = time.perf_counter()
                result = adapter.recognize(image, **kwargs)
                rows.append({"engine": name, "seconds": round(time.perf_counter() - started, 3), "ok": True, "result": result})
            except Exception as exc:
                rows.append({"engine": name, "seconds": 0, "ok": False, "error": str(exc)})
        return rows


def tesseract_adapter() -> EngineAdapter:
    def available() -> bool:
        try:
            import pytesseract
            return bool(pytesseract.get_tesseract_version())
        except Exception:
            return False

    def recognize(image, **kwargs):
        import pytesseract
        return pytesseract.image_to_string(image, **kwargs)

    return EngineAdapter(EngineInfo("Tesseract", "Bundled/default OCR engine", optional=False), available, recognize)


def default_manager() -> OCREngineManager:
    manager = OCREngineManager()
    manager.register(tesseract_adapter())
    return manager
