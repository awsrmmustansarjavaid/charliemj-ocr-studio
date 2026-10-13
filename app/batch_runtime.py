"""Reliable unlimited-queue OCR runtime patch.

This module is intentionally additive: the existing four-panel UI, OCR engine,
layout engine, editor and result cards remain intact.  It fixes one important
batch-state bug: the old Process All command skipped records whose previous OCR
status was already ``done``.  That meant an image previously processed as Raw
was never re-run after switching to Smart or AI Smart.

The runtime also removes the artificial image-count cap and adds explicit
all-image buttons for Smart, Raw and local Ollama AI processing.
"""
from __future__ import annotations

import threading

import customtkinter as ctk

from .config import cfg


def batch_plan(items, mode):
    """Return every top-level image exactly once, regardless of previous status."""
    return [(item, mode) for item in list(items)]


def _unlimited_add_image(self, img, name, at=None, show=True):
    """Replacement for App.add_image with no queue-size limit."""
    self.save_cards()
    item = self.new_item(img, name)
    index = len(self.items) if at is None else at
    self.items.insert(index, item)
    self.refresh_all()
    if show:
        self.show(self.items.index(item))
    return item


def _unlimited_undo_remove(self):
    """Restore all removed images; the queue is no longer capped."""
    for i, item in sorted(self.removed, key=lambda x: x[0]):
        self.items.insert(min(i, len(self.items)), item)
    self.removed = []
    self.refresh_all()
    self.sync_editor()


def _refresh_all_unlimited(self):
    """Keep the existing redraw logic but show a truthful unlimited queue count."""
    self._batch_original_refresh_all()
    try:
        self.count.configure(text=f"Images: {len(self.items)}  •  Unlimited")
    except Exception:
        pass


def _process_all_everything(self, mode=None):
    """Process every attached image in the selected mode, even if it was processed before."""
    if not self.items:
        return self.status("Add at least one image first")

    selected_mode = mode or self.mode.get()
    accuracy = self.accuracy.get()  # capture Tk state before entering the worker
    todo = list(self.items)
    total = len(todo)
    self.save_cards()
    self.progress.set(0)
    self.progress.pack(side="left", padx=12)
    self.status(f"Scanning {total} image(s) — {selected_mode} / {accuracy}…")

    def worker():
        completed = 0
        failures = 0
        for number, item in enumerate(todo, 1):
            self.post(lambda item=item, number=number: (
                self.set_status(item, "working"),
                self.progress.set((number - 1) / total),
                self.status(f"Processing image {number} / {total} ({selected_mode}, {accuracy})…")
            ))
            try:
                result = self.read(item, selected_mode)
            except Exception as exc:
                failures += 1
                message = str(exc) or exc.__class__.__name__
                self.post(lambda item=item, message=message: (
                    self.set_status(item, "error"),
                    self.status(f"⚠ Image {todo.index(item) + 1}: {message[:180]}")
                ))
                continue

            completed += 1
            self.post(lambda item=item, result=result: self.apply(item, *result))

        def finish():
            self.progress.set(1)
            self.progress.pack_forget()
            self.refresh_all()
            self.sync_editor()
            if failures:
                self.status(f"✓ Finished {completed}/{total}; {failures} image(s) need attention")
            else:
                self.status(f"✓ Finished all {total} image(s) — {selected_mode}")

        self.post(finish)

    threading.Thread(target=worker, daemon=True, name="ocr-batch-all").start()


def _ocr_current_force(self):
    """Re-run the selected image using the currently selected OCR mode."""
    if self.current is None:
        if self.items:
            self.current = 0
        else:
            return self.status("Select an image first")
    self.run_ocr(self.items[self.current], self.mode.get())


def _add_batch_controls(self, parent):
    """Add explicit controls so users never have to infer how to process all images."""
    ctk.CTkButton(
        parent, text="🔎 Scan All Images", height=34,
        command=lambda: self.process_all("Smart")
    ).pack(fill="x", padx=10, pady=3)
    ctk.CTkButton(
        parent, text="🤖 AI Smart All (Ollama)", height=34,
        fg_color="#6b46c1", hover_color="#805ad5",
        command=lambda: self.process_all("AI Smart")
    ).pack(fill="x", padx=10, pady=3)


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


def install(AppClass):
    """Patch App before its constructor binds button callbacks."""
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
    AppClass.build_queue = _build_queue_unlimited
    AppClass.build_preview = _build_preview_unlimited
    AppClass._unlimited_batch_runtime = True
