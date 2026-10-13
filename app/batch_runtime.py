"""Reliable unlimited-queue OCR runtime patch.

This module is intentionally additive: the existing four-panel UI, OCR engine,
layout engine, editor and result cards remain intact. It fixes the batch-state
bug where Process All skipped images that already had a ``done`` result.
"""
from __future__ import annotations

import threading
import tkinter as tk

import customtkinter as ctk

from .config import cfg
from . import local_agents


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
                self.post(lambda item=item, message=message, number=number: (
                    self.set_status(item, "error"),
                    self.status(f"⚠ Image {number}: {message[:180]}")
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


def _open_agents(self):
    """Show the local Ollama agent panel without introducing a cloud dependency."""
    app = self
    win = ctk.CTkToplevel(app)
    win.title("Local AI Agents — Ollama")
    win.geometry("760x560")
    win.minsize(620, 440)

    top = ctk.CTkFrame(win); top.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(top, text="LOCAL AI AGENTS", font=("Segoe UI", 15, "bold")).pack(side="left")
    ctk.CTkLabel(top, text=f"Ollama: {cfg['ollama_url']}  •  Model: {cfg['model']}", text_color="gray").pack(side="right")

    source = ctk.CTkTextbox(win, height=120, font=("Consolas", 11)); source.pack(fill="x", padx=10, pady=5)
    if getattr(app, "current", None) is not None and app.items:
        current = app.items[app.current]
        source.insert("1.0", current.get("raw") or current.get("md") or "")
    else:
        source.insert("1.0", app.combined_text() if app.items else "")

    output = ctk.CTkTextbox(win, font=("Segoe UI", 12)); output.pack(fill="both", expand=True, padx=10, pady=5)
    status = ctk.CTkLabel(win, text="Choose an agent. All requests stay on localhost.", anchor="w")
    status.pack(fill="x", padx=10, pady=4)

    buttons = ctk.CTkFrame(win); buttons.pack(fill="x", padx=10, pady=8)
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
                status.configure(text=f"⚠ {message[:220]}")
            app.bg(lambda: local_agents.run(name, text, image), done, fail)
        ctk.CTkButton(buttons, text=agent_name, command=run_agent).pack(side="left", padx=3)
    ctk.CTkButton(buttons, text="Close", command=win.destroy).pack(side="right", padx=3)


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
    ctk.CTkButton(
        parent, text="🧠 Local AI Agents", height=34,
        fg_color="#4b2e83", hover_color="#6341a1",
        command=self._open_agents
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
    ctk.CTkButton(parent, text="🧠 Agents", command=self._open_agents).pack(fill="x", padx=8, pady=(0, 8))


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
    AppClass._open_agents = _open_agents
    AppClass.build_queue = _build_queue_unlimited
    AppClass.build_preview = _build_preview_unlimited
    AppClass._unlimited_batch_runtime = True
