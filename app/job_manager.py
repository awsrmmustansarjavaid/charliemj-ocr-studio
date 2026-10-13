"""Thread-safe OCR job orchestration used by the desktop UI.

The manager deliberately knows nothing about Tkinter.  It owns the worker
lifecycle and per-image state while the UI supplies callbacks that are executed
on the UI thread by App.post().  This prevents one failed image from wedging the
whole queue and makes individual and batch OCR follow the same execution path.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import threading
import uuid
from typing import Callable, Iterable, Any


@dataclass
class OCRJob:
    job_id: str
    number: int
    total: int
    item: Any
    mode: str
    status: str = "queued"
    started_at: str = ""
    finished_at: str = ""
    error: str = ""
    result: Any = None


class OCRJobManager:
    """Run OCR jobs sequentially with cancellation and explicit per-image state."""

    def __init__(self, log: Callable[[str, str, str], None] | None = None):
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._jobs: list[OCRJob] = []
        self._log = log

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @property
    def running(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    @property
    def jobs(self) -> list[OCRJob]:
        with self._lock:
            return list(self._jobs)

    def cancel(self) -> None:
        self._cancel.set()

    def start(
        self,
        items: Iterable[Any],
        mode: str,
        worker: Callable[[Any, str], Any],
        on_start: Callable[[OCRJob], None] | None = None,
        on_result: Callable[[OCRJob], None] | None = None,
        on_error: Callable[[OCRJob], None] | None = None,
        on_finish: Callable[[list[OCRJob]], None] | None = None,
    ) -> bool:
        """Start a new sequential job set. Returns False when another run is active."""
        with self._lock:
            if self.running:
                return False
            selected = list(items)
            self._cancel.clear()
            self._jobs = [OCRJob(uuid.uuid4().hex[:10], i, len(selected), item, mode)
                          for i, item in enumerate(selected, 1)]
            jobs = list(self._jobs)

            def run() -> None:
                for job in jobs:
                    if self._cancel.is_set():
                        job.status = "cancelled"
                        job.finished_at = self._now()
                        self._emit("cancelled", job)
                        continue
                    job.status = "working"
                    job.started_at = self._now()
                    self._emit("start", job)
                    if on_start:
                        on_start(job)
                    try:
                        job.result = worker(job.item, job.mode)
                    except Exception as exc:  # one image must never stop the queue
                        job.status = "error"
                        job.error = str(exc) or exc.__class__.__name__
                        job.finished_at = self._now()
                        self._emit("error", job)
                        if on_error:
                            on_error(job)
                    else:
                        job.status = "done"
                        job.finished_at = self._now()
                        self._emit("done", job)
                        if on_result:
                            on_result(job)
                if on_finish:
                    on_finish(list(jobs))

            self._thread = threading.Thread(target=run, daemon=True, name="ocr-job-manager")
            self._thread.start()
            return True

    def _emit(self, stage: str, job: OCRJob) -> None:
        if self._log:
            try:
                self._log(stage, job.mode, self._describe(job))
            except Exception:
                pass

    @staticmethod
    def _describe(job: OCRJob) -> str:
        item = job.item
        name = str(item.get("name", "image")) if isinstance(item, dict) else "image"
        return f"job={job.job_id} image={job.number}/{job.total} name={name!r} status={job.status} error={job.error!r}"
