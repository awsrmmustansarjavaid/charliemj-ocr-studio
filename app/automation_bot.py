"""OCR Automation Bot for large image folders.

Stream mode intentionally keeps only the active image in the OCR queue, so a
folder with hundreds or thousands of screenshots does not require all PIL
images to remain in RAM at once.
"""
from __future__ import annotations

import csv
import json
import os
import threading
import time
import customtkinter as ctk
from tkinter import filedialog

from .config import EXTS
from . import diagnostics


class AutomationBot(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.paths: list[str] = []
        self.running = False
        self.stop_event = threading.Event()
        self.title("Charlie MJ — OCR Automation Bot")
        self.geometry("900x680")
        self.minsize(760, 560)
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self); top.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(top, text="Choose Folder", command=self.choose_folder).pack(side="left", padx=4)
        ctk.CTkButton(top, text="Clear", command=self.clear).pack(side="left", padx=4)
        self.info = ctk.CTkLabel(top, text="No folder selected", anchor="w"); self.info.pack(side="left", padx=12)
        form = ctk.CTkFrame(self); form.pack(fill="x", padx=10, pady=4)
        self.mode = ctk.CTkOptionMenu(form, values=["Smart", "Raw", "AI Smart"]); self.mode.set("Smart"); self.mode.pack(side="left", padx=4)
        self.ext = ctk.CTkOptionMenu(form, values=["Markdown", "Text", "JSON", "CSV"]); self.ext.set("Markdown"); self.ext.pack(side="left", padx=4)
        self.output_dir = ctk.CTkEntry(form, placeholder_text="Output folder"); self.output_dir.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(form, text="Browse", command=self.choose_output).pack(side="left", padx=4)
        self.keep = ctk.CTkCheckBox(form, text="Keep results in queue"); self.keep.select(); self.keep.pack(side="left", padx=6)
        self.list_box = ctk.CTkTextbox(self, font=("Consolas", 11)); self.list_box.pack(fill="both", expand=True, padx=10, pady=8)
        row = ctk.CTkFrame(self); row.pack(fill="x", padx=10, pady=8)
        self.start_btn = ctk.CTkButton(row, text="▶ Start Bot", height=38, command=self.start); self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ctk.CTkButton(row, text="⏹ Stop", height=38, command=self.stop); self.stop_btn.pack(side="left", padx=4)
        self.progress = ctk.CTkProgressBar(row); self.progress.pack(side="left", fill="x", expand=True, padx=12); self.progress.set(0)
        self.status = ctk.CTkLabel(self, text="Ready", anchor="w"); self.status.pack(fill="x", padx=12, pady=(0, 8))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Select OCR image folder")
        if not folder: return
        self.paths = [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.lower().endswith(EXTS)]
        self.info.configure(text=f"{len(self.paths)} image(s)")
        self.list_box.delete("1.0", "end")
        self.list_box.insert("1.0", "\n".join(self.paths[:500]))
        if len(self.paths) > 500: self.list_box.insert("end", f"\n… and {len(self.paths)-500} more")

    def choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir.delete(0, "end"); self.output_dir.insert(0, folder)

    def clear(self):
        self.paths = []; self.list_box.delete("1.0", "end"); self.info.configure(text="No folder selected")

    def start(self):
        if self.running: return
        if not self.paths:
            return self.status.configure(text="Choose a folder containing images first.")
        output = self.output_dir.get().strip()
        if not output:
            output = os.path.join(os.path.dirname(self.paths[0]), "ocr-output")
            self.output_dir.insert(0, output)
        os.makedirs(output, exist_ok=True)
        self.running = True; self.stop_event.clear(); self.start_btn.configure(state="disabled")
        threading.Thread(target=self._worker, args=(list(self.paths), self.mode.get(), self.ext.get(), output, self.keep.get()), daemon=True, name="ocr-automation-bot").start()

    def stop(self):
        self.stop_event.set()
        if hasattr(self.app, "cancel_ocr"): self.app.cancel_ocr()
        self.status.configure(text="Stop requested — finishing the current image safely…")

    def _worker(self, paths, mode, ext, output, keep):
        completed = 0
        for index, path in enumerate(paths, 1):
            if self.stop_event.is_set(): break
            name = os.path.basename(path)
            self.app.post(lambda index=index, total=len(paths), name=name: (self.progress.set((index-1)/total), self.status.configure(text=f"Bot: {index}/{total} — {name}")))
            try:
                from PIL import Image
                image = Image.open(path).convert("RGB")
                holder = {"done": False, "item": None}
                def add_and_start():
                    item = self.app.add_image(image, name, show=False)
                    holder["item"] = item
                    if item is None: raise RuntimeError("Could not add image to OCR queue")
                    self.app.run_ocr(item, mode)
                self.app.post(add_and_start)
                deadline = time.time() + 1800
                while time.time() < deadline and not self.stop_event.is_set():
                    time.sleep(0.25)
                    item = holder["item"]
                    if item is not None and item.get("status") in ("done", "error"):
                        break
                item = holder["item"]
                if item is None or item.get("status") != "done":
                    raise RuntimeError("OCR job did not complete")
                self._export_item(item, path, ext, output)
                completed += 1
                if not keep:
                    self.app.post(lambda item=item: self.app.remove_items([item]))
            except Exception as exc:
                diagnostics.log("BOT", f"file={path!r} error={exc!r}", "ERROR")
                self.app.post(lambda name=name, exc=exc: self.status.configure(text=f"⚠ {name}: {exc}"))
        self.app.post(lambda: self._finished(completed, len(paths)))

    def _export_item(self, item, source_path, ext, output):
        base = os.path.splitext(os.path.basename(source_path))[0]
        text = self.app.item_text(item)
        target_ext = {"Markdown": ".md", "Text": ".txt", "JSON": ".json", "CSV": ".csv"}[ext]
        target = os.path.join(output, base + target_ext)
        if ext == "JSON":
            payload = {"source": source_path, "name": item.get("name"), "raw": item.get("raw", ""), "result": text}
            with open(target, "w", encoding="utf-8") as fh: json.dump(payload, fh, ensure_ascii=False, indent=2)
        elif ext == "CSV":
            with open(target, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh); w.writerow(["source", "text"]); w.writerow([source_path, text])
        else:
            with open(target, "w", encoding="utf-8") as fh: fh.write(text)

    def _finished(self, completed, total):
        self.running = False; self.start_btn.configure(state="normal"); self.progress.set(1 if total else 0)
        self.status.configure(text=f"✓ Bot finished: {completed}/{total} image(s) exported")
        diagnostics.log("BOT", f"finished completed={completed} total={total}")
