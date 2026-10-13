"""Small local diagnostics/logging helpers for OCR troubleshooting.

Logs are plain UTF-8 text next to the portable application's config file.  No
image pixels, OCR text, prompts, or AI responses are written by this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
import os
import threading

from .config import BASE

LOG_PATH = os.path.join(BASE, "ocr-studio.log")
_lock = threading.RLock()


def log(stage: str, message: str, level: str = "INFO") -> None:
    """Append one timestamped diagnostic line; logging can never break OCR."""
    try:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        line = f"{stamp} [{level}] [{stage}] {message}\n"
        with _lock:
            with open(LOG_PATH, "a", encoding="utf-8") as fh:
                fh.write(line)
    except Exception:
        pass


def recent(limit: int = 300) -> str:
    """Return the newest diagnostic lines for a Troubleshooting/Health UI."""
    try:
        with _lock:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        return "".join(lines[-max(1, int(limit)):])
    except FileNotFoundError:
        return "No OCR Studio log has been created yet."
    except Exception as exc:
        return f"Unable to read OCR Studio log: {exc}"


def clear() -> None:
    """Clear the local diagnostic log."""
    try:
        with _lock:
            if os.path.exists(LOG_PATH):
                os.remove(LOG_PATH)
    except Exception:
        pass


def report() -> dict[str, str]:
    """Return safe environment facts for a future Health Check panel."""
    import sys
    from . import __version__

    return {
        "version": str(__version__),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "log_path": LOG_PATH,
    }
