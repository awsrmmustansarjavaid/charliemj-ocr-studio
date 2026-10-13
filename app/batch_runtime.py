"""Reliable unlimited-queue OCR runtime and per-image job integration.

The existing four-panel UI remains intact. All top-level images are eligible
for processing, regardless of their previous status. Individual OCR and batch
OCR use the same job manager so every image gets explicit start/result/error
handling and diagnostics.
"""
from __future__ import annotations

import customtkinter as ctk

from .config import cfg
from . import diagnostics, local_agents
from .job_manager import OCRJob, OCRJobManager


def batch_plan(items, mode):
    """Return every top-level image exactly once, with no status/count filtering."""
    return [(item, mode) for item in list(items)]


def _unlimited_add_image(self, img, name, at=None, show=True):
    """Replacement for App.add_image with no application-imposed queue cap."""
    self.save_cards()
    item = self.new_item(img, name)
    index = len(self.items) if at is None else at
    self.items.insert(index, item)
    self.refresh_all()
    if show:
        self.show(self.items.index(item))
    diagnostics.log("QUEUE", f"added image name={name!r} total={len(self.items)}")
    return item


def _unlimited_undo_remove(self):
    """Restore every removed image; the queue is no longer capped."""
    for i, item in sorted(self.removed, key=lambda x: x[0]):
        self.items.insert(min(i, len(self.items)), item)
    self.removed = []
    self.refresh_all()
    self.sync_editor()
    diagnostics.log("QUEUE", f"undo restored total={len(self.items)}")


def _refresh_all_unlimited(self):
    self._batch_original_refresh_all()
    try:
        self.count.configure(text=f"Images: {len(self.items)}  •  Unlimited")
    except Exception:
        pass


def _job_log(stage: str, mode: str, detail: str) -> None:
    diagnostics.log("OCR-JOB", f"{stage} mode={mode} {detail}")


def _ensure_job_manager(self):
    manager = getattr(self, "_ocr_job_manager", None)
    if manager is None:
        manager = OCRJobManager(log=_job_log)
        self._ocr_job_manager = manager
    return manager


def _job_name(job: OCRJob) -> str:
    return str(job.item.get("name", f"image {job.number}"))


def _ui_job_start(self, job: OCRJob, accuracy: str) -> None:
    self.set_status(job.item, "working")
    self.progress.set((job.number - 1) / max(1, job.total))
    self.status(f"Processing image {job.number} / {job.total} ({job.mode}, {accuracy})…")
    diagnostics.log("OCR-START", f"image={job.number}/{job.total} name={_job_name(job)!r} mode={job.mode} accuracy={accuracy}")


def _ui_job_result(self, job: OCRJob) -> None:
    """Commit exactly one result on the UI thread, then redraw that image."""
    item = job.item
    try:
        info = self.apply(item, *job.result)
        owner = item.get("parent") or item
        self.refresh_card(owner)
        self.set_status(item, "done")
        self.sync_editor()
        diagnostics.log("OCR-APPLY", f"image={job.number}/{job.total} name={_job_name(job)!r} mode={job.mode} result={info[:160]!r}")
        self.status(info if info.startswith("⚠") else "✓ " + info)
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        self.set_status(item, "error")
        diagnostics.log("OCR-APPLY", f"image={job.number}/{job.total} name={_job_name(job)!r} mode={job.mode} error={message!r}", "ERROR")
        self.status(f"⚠ Image {job.number} result could not be applied: {message[:180]}")


def _ui_job_error(self, job: OCRJob) -> None:
    self.set_status(job.item, "error")
    diagnostics.log("OCR-ERROR", f"image={job.number}/{job.total} name={_job_name(job)!r} mode={job.mode} error={job.error!r}", "ERROR")
    self.status(f"⚠ Image {job.number}: {job.error[:180]}")


def _ui_job_finish(self, jobs, selected_mode: str) -> None:
    self.progress.set(1)
    self.progress.pack_forget()
    self.refresh_all()
    self.sync_editor()
    done = sum(j.status == "done" for j in jobs)
    failed = sum(j.status == "error" for j in jobs)
    cancelled = sum(j.status == "cancelled" for j in jobs)
    total = len(jobs)
    if failed or cancelled:
        self.status(f"✓ Finished {done}/{total} image(s); {failed} failed; {cancelled} cancelled")
    else:
        self.status(f"✓ Finished all {total} image(s) — {selected_mode}")
    diagnostics.log("OCR-FINISH", f"mode={selected_mode} total={total} done={done} failed={failed} cancelled={cancelled}")


def _start_jobs(self, items, mode: str) -> bool:
    """Start jobs through one code path used by both single-image and batch OCR."""
    if not items:
        self.status("Add/select an image first")
        return False
    manager = _ensure_job_manager(self)
    if manager.running:
        self.status("⚠ OCR is already running. Wait for the current job set to finish.")
        return False

    accuracy = self.accuracy.get()
    selected = list(items)
    self.save_cards()
    self.progress.set(0)
    self.progress.pack(side="left", padx=12)
    self.status(f"Starting {len(selected)} image(s) — {mode} / {accuracy}…")

    def worker(item, selected_mode):
        diagnostics.log("OCR-WORKER", f"begin name={item.get('name', 'image')!r} mode={selected_mode}")
        return self.read(item, selected_mode)

    def start(job):
        self.post(lambda job=job: _ui_job_start(self, job, accuracy))

    def result(job):
        self.post(lambda job=job: _ui_job_result(self, job))

    def error(job):
        self.post(lambda job=job: _ui_job_error(self, job))

    def finish(jobs):
        self.post(lambda jobs=jobs: _ui_job_finish(self, jobs, mode))

    return manager.start(selected, mode, worker, start, result, error, finish)


def _process_all_everything(self, mode=None):
    """Process every attached image, including images already marked done."""
    selected_mode = mode or self.mode.get()
    return _start_jobs(self, list(self.items), selected_mode)


def _ocr_current_force(self):
    """Re-run the selected image through the exact same job path as batch OCR."""
    if self.current is None:
        if self.items:
            self.current = 0
        else:
            return self.status("Select an image first")
    return _start_jobs(self, [self.items[self.current]], self.mode.get())


def _run_ocr_unified(self, rec, mode):
    """Run a card's Smart/Raw/AI button through the same manager as batch OCR.

    The original UI.run_ocr used App.bg directly, which meant clicking a card
    button took a different execution path from Process All. That made an
    individual image appear to finish without receiving the same committed
    result handling. All OCR entry points now share _start_jobs().
    """
    return _start_jobs(self, [rec], mode)


def _cancel_ocr(self):
    manager = getattr(self, "_ocr_job_manager", None)
    if manager and manager.running:
        manager.cancel()
        self.status("Cancelling OCR after the current image…")
        diagnostics.log("OCR-CANCEL", "cancel requested")
    else:
        self.status("No OCR job is running")


def _open_agents(self):
    """Show local Ollama agents with actionable connection diagnostics."""
    app = self
    win = ctk.CTkToplevel(app)
    win.title("Local AI Agents — Ollama")
    win.geometry("760x600")
    win.minsize(620, 480)

    top = ctk.CTkFrame(win)
    top.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(top, text="LOCAL AI AGENTS", font=("Segoe UI", 15, "bold")).pack(side="left")
    ctk.CTkLabel(top, text=f"Ollama: {cfg['ollama_url']}  •  Model: {cfg['model']}", text_color="gray").pack(side="right")

    source = ctk.CTkTextbox(win, height=120, font=("Consolas", 11))
    source.pack(fill="x", padx=10, pady=5)
    if getattr(app, "current", None) is not None and app.items:
        current = app.items[app.current]
        source.insert("1.0", current.get("raw") or current.get("md") or "")
    else:
        source.insert("1.0", app.combined_text() if app.items else "")

    output = ctk.CTkTextbox(win, font=("Segoe UI", 12))
    output.pack(fill="both", expand=True, padx=10, pady=5)
    status = ctk.CTkLabel(win, text="Checking Ollama…", anchor="w")
    status.pack(fill="x", padx=10, pady=4)

    def check():
        status.configure(text="Checking Ollama connection and installed models…")
        def done(result):
            ok, names, msg = result
            if ok:
                status.configure(text=f"✓ Ollama connected • {len(names)} model(s) available • selected: {cfg['model']}")
            else:
                status.configure(text=f"✕ Ollama unavailable: {msg}. Start Ollama, then press Check again.")
        app.bg(lambda: local_agents.status(), done,
               lambda msg: status.configure(text=f"✕ Ollama diagnostic failed: {msg[:220]}"))

    ctk.CTkButton(top, text="Check", width=90, command=check).pack(side="right", padx=(8, 0))

    buttons = ctk.CTkFrame(win)
    buttons.pack(fill="x", padx=10, pady=8)
    for agent_name in local_agents.names():
        def run_agent(name=agent_name):
            text = source.get("1.0", "end").strip()
            image = None
            if getattr(app, "current", None) is not None and app.items:
                image = app.items[app.current].get("img")
            if not text and image is None:
                status.configure(text="Add/process an image first")
                return
            status.configure(text=f"🤖 {name} running locally…")
            def done(result):
                output.delete("1.0", "end")
                output.insert("1.0", result)
                status.configure(text=f"✓ {name} complete")
            def fail(message):
                diagnostics.log("LOCAL-AI", f"agent={name!r} error={message!r}", "ERROR")
                status.configure(text=f"⚠ {message[:220]}")
            app.bg(lambda: local_agents.run(name, text, image), done, fail)
        ctk.CTkButton(buttons, text=agent_name, command=run_agent).pack(side="left", padx=3)
    ctk.CTkButton(buttons, text="Close", command=win.destroy).pack(side="right", padx=3)
    check()


def _add_batch_controls(self, parent):
    ctk.CTkButton(parent, text="🔎 Scan All Images", height=34,
                  command=lambda: self.process_all("Smart")).pack(fill="x", padx=10, pady=3)
    ctk.CTkButton(parent, text="🤖 AI Smart All (Ollama)", height=34,
                  fg_color="#6b46c1", hover_color="#805ad5",
                  command=lambda: self.process_all("AI Smart")).pack(fill="x", padx=10, pady=3)
    ctk.CTkButton(parent, text="🧠 Local AI Agents", height=34,
                  fg_color="#4b2e83", hover_color="#6341a1",
                  command=self._open_agents).pack(fill="x", padx=10, pady=3)
    ctk.CTkButton(parent, text="⏹ Cancel OCR", height=30, command=self.cancel_ocr,
                  **{"fg_color": "gray30"}).pack(fill="x", padx=10, pady=3)


def _build_queue_unlimited(self, parent):
    self._batch_original_build_queue(parent)
    _add_batch_controls(self, parent)


def _build_preview_unlimited(self, parent):
    self._batch_original_build_preview(parent)
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=8, pady=(0, 8))
    ctk.CTkButton(row, text="Scan All", command=lambda: self.process_all("Smart")).pack(side="left", expand=True, fill="x", padx=2)
    ctk.CTkButton(row, text="AI All", fg_color="#6b46c1", hover_color="#805ad5",
                  command=lambda: self.process_all("AI Smart")).pack(side="left", expand=True, fill="x", padx=2)
    ctk.CTkButton(parent, text="🧠 Agents", command=self._open_agents).pack(fill="x", padx=8, pady=(0, 8))


def install(AppClass):
    """Patch App before its constructor binds callbacks."""
    if getattr(AppClass, "_unlimited_batch_runtime", False):
        return

    AppClass._batch_original_refresh_all = AppClass.refresh_all
    AppClass._batch_original_build_queue = AppClass.build_queue
    AppClass._batch_original_build_preview = AppClass.build_preview

    AppClass.add_image = _unlimited_add_image
    AppClass.undo_remove = _unlimited_undo_remove
    AppClass.refresh_all = _refresh_all_unlimited
    AppClass.process_all = _process_all_everything
    AppClass.ocr_current = _ocr_current_force
    AppClass.run_ocr = _run_ocr_unified
    AppClass.cancel_ocr = _cancel_ocr
    AppClass._open_agents = _open_agents
    AppClass.build_queue = _build_queue_unlimited
    AppClass.build_preview = _build_preview_unlimited
    AppClass._unlimited_batch_runtime = True
