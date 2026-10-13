"""GUI workspace for vocabulary, flashcards, projects, dictionary and OCR engines.

Installed from main.py as an additive menu. It does not replace the existing four-panel OCR UI.
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from .dictionary import Dictionary, DictionaryEntry
from .features import default_manager
from .flashcards import Flashcard, due_cards
from .project_store import load_project, save_project
from .study_workspace import StudyWorkspace
from .vocabulary import VocabularyEntry, to_anki, to_csv, to_json
from .config import BASE, cfg


class StudyWorkspaceWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Charlie MJ — Study Workspace")
        self.geometry("1050x700")
        self.minsize(800, 560)
        self.workspace = StudyWorkspace(Dictionary(os.path.join(BASE, "dictionary.json")))
        self.engine_manager = default_manager()
        self._build(); self._refresh_all(); self.transient(app)

    def _build(self):
        bar = ctk.CTkFrame(self); bar.pack(fill="x", padx=8, pady=8)
        for text, cmd in (("Extract from OCR", self.extract_ocr), ("Generate Flashcards", self.generate_cards),
                          ("Save Project", self.save_project_dialog), ("Open Project", self.open_project_dialog)):
            ctk.CTkButton(bar, text=text, command=cmd).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="Close", command=self.destroy).pack(side="right", padx=3)
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.vocab_tab = self.tabs.add("Vocabulary"); self.cards_tab = self.tabs.add("Flashcards")
        self.dict_tab = self.tabs.add("Dictionary"); self.project_tab = self.tabs.add("Project"); self.engine_tab = self.tabs.add("OCR Engines")
        self._build_vocab(); self._build_cards(); self._build_dict(); self._build_project(); self._build_engines()

    def _build_vocab(self):
        top = ctk.CTkFrame(self.vocab_tab); top.pack(fill="x", padx=8, pady=8)
        self.vocab_stats = ctk.CTkLabel(top, text="Vocabulary: 0"); self.vocab_stats.pack(side="left")
        for text, ext in (("Export CSV", "csv"), ("Export JSON", "json"), ("Export Anki", "txt")):
            ctk.CTkButton(top, text=text, width=120, command=lambda ext=ext: self.export_vocab(ext)).pack(side="right", padx=2)
        self.vocab_box = ctk.CTkTextbox(self.vocab_tab, font=("Consolas", 13)); self.vocab_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_cards(self):
        top = ctk.CTkFrame(self.cards_tab); top.pack(fill="x", padx=8, pady=8)
        self.card_status = ctk.CTkLabel(top, text="No cards"); self.card_status.pack(side="left")
        self.card_box = ctk.CTkTextbox(self.cards_tab, font=("Segoe UI", 14)); self.card_box.pack(fill="both", expand=True, padx=8, pady=8)
        row = ctk.CTkFrame(self.cards_tab); row.pack(fill="x", padx=8, pady=8)
        for label, quality in (("Again", 1), ("Hard", 3), ("Good", 4), ("Easy", 5)):
            ctk.CTkButton(row, text=label, command=lambda q=quality: self.review_card(q)).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Export TSV", command=self.export_cards).pack(side="right")

    def _build_dict(self):
        form = ctk.CTkFrame(self.dict_tab); form.pack(fill="x", padx=8, pady=8)
        self.dict_source = ctk.CTkEntry(form, placeholder_text="Word / phrase"); self.dict_source.pack(side="left", fill="x", expand=True, padx=4)
        self.dict_translation = ctk.CTkEntry(form, placeholder_text="Translation"); self.dict_translation.pack(side="left", fill="x", expand=True, padx=4)
        ctk.CTkButton(form, text="Save", command=self.save_dictionary_entry).pack(side="left", padx=4)
        ctk.CTkButton(form, text="Lookup", command=self.lookup_dictionary).pack(side="left", padx=4)
        self.dict_box = ctk.CTkTextbox(self.dict_tab); self.dict_box.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_project(self):
        self.project_info = ctk.CTkTextbox(self.project_tab); self.project_info.pack(fill="both", expand=True, padx=8, pady=8)
        self.project_info.insert("1.0", "Projects keep images and OCR/learning metadata together.\n")

    def _build_engines(self):
        self.engine_box = ctk.CTkTextbox(self.engine_tab); self.engine_box.pack(fill="both", expand=True, padx=8, pady=8)
        ctk.CTkButton(self.engine_tab, text="Refresh engine status", command=self.refresh_engines).pack(pady=8); self.refresh_engines()

    def extract_ocr(self):
        self.workspace.vocabulary = []; count = 0
        for item in self.app.items:
            count += self.workspace.ingest_markdown(item.get("md", ""), cfg["lang"], item.get("name", ""))
            for area in item.get("areas", []):
                count += self.workspace.ingest_markdown(area.get("md", ""), cfg["lang"], f"{item.get('name','')} / Area {area.get('n','')}")
        self.workspace.enrich_from_dictionary(); self._refresh_vocab()
        self.card_status.configure(text=f"Added {count} new vocabulary item(s)")

    def generate_cards(self):
        added = self.workspace.make_flashcards(); self._refresh_cards(); self.card_status.configure(text=f"Added {added} flashcard(s)")

    def _refresh_vocab(self):
        self.vocab_box.delete("1.0", "end")
        for i, e in enumerate(self.workspace.vocabulary, 1): self.vocab_box.insert("end", f"{i:03d}  {e.source}  —  {e.translation}\n")
        s = self.workspace.statistics(); self.vocab_stats.configure(text=f"Vocabulary: {s['total']}   New: {s['new']}   Known: {s['known']}   Difficult: {s['difficult']}")

    def _refresh_cards(self):
        self.card_box.delete("1.0", "end")
        for i, c in enumerate(self.workspace.flashcards, 1): self.card_box.insert("end", f"{i:03d}  {c.front}  →  {c.back}   due={c.due or 'now'}\n")
        self.card_status.configure(text=f"Cards: {len(self.workspace.flashcards)}   Due: {len(due_cards(self.workspace.flashcards))}")

    def _refresh_all(self):
        self._refresh_vocab(); self._refresh_cards(); self.refresh_dictionary(); self.refresh_engines()

    def review_card(self, quality):
        due = due_cards(self.workspace.flashcards)
        if not due: self.card_status.configure(text="No cards due"); return
        due[0].review(quality); self._refresh_cards()

    def export_vocab(self, ext):
        path = filedialog.asksaveasfilename(defaultextension="." + ext, filetypes=[("Vocabulary", "*." + ext)])
        if not path: return
        text = {"csv": to_csv, "json": to_json, "txt": to_anki}[ext](self.workspace.vocabulary)
        with open(path, "w", encoding="utf-8", newline="") as f: f.write(text)
        self.vocab_stats.configure(text=f"Exported {len(self.workspace.vocabulary)} item(s)")

    def export_cards(self):
        path = filedialog.asksaveasfilename(defaultextension=".tsv", filetypes=[("Anki TSV", "*.tsv")])
        if not path: return
        from .flashcards import to_tsv
        with open(path, "w", encoding="utf-8", newline="") as f: f.write(to_tsv(self.workspace.flashcards))

    def save_dictionary_entry(self):
        source, translation = self.dict_source.get().strip(), self.dict_translation.get().strip()
        if source: self.workspace.dictionary.put(DictionaryEntry(source, translation, language=cfg["lang"])); self.refresh_dictionary()

    def lookup_dictionary(self):
        entry = self.workspace.lookup(self.dict_source.get()); self.dict_translation.delete(0, "end")
        if entry: self.dict_translation.insert(0, entry.translation)

    def refresh_dictionary(self):
        self.dict_box.delete("1.0", "end")
        for e in self.workspace.dictionary.values(): self.dict_box.insert("end", f"{e.source}  —  {e.translation}\n")

    def refresh_engines(self):
        self.engine_box.delete("1.0", "end")
        for row in self.engine_manager.status():
            state = "available" if row["available"] else "unavailable"
            self.engine_box.insert("end", f"{row['name']}: {state} — {row['description']}\n")

    def save_project_dialog(self):
        path = filedialog.askdirectory(title="Choose project folder")
        if not path: return
        records, images = [], []
        for item in self.app.items:
            images.append((item["img"], item["name"]))
            records.append({"name": item["name"], "kind": item.get("kind", ""), "md": item.get("md", ""), "raw": item.get("raw", "")})
        manifest = {"name": os.path.basename(path), "language": cfg["lang"], "native": cfg["native"], "items": records,
                    "vocabulary": [e.__dict__ for e in self.workspace.vocabulary], "flashcards": [c.__dict__ for c in self.workspace.flashcards]}
        save_project(path, manifest, images)
        self.project_info.delete("1.0", "end"); self.project_info.insert("1.0", json.dumps(manifest, ensure_ascii=False, indent=2))

    def open_project_dialog(self):
        path = filedialog.askdirectory(title="Open Charlie MJ project")
        if not path: return
        try: manifest = load_project(path)
        except Exception as exc: messagebox.showerror("Project", str(exc)); return
        if self.app.items and not messagebox.askyesno("Open project", "Replace the current OCR queue with this project?"): return
        if self.app.items:
            self.app.save_cards(); self.app.items = []; self.app.removed = []; self.app.clear_preview()
        loaded = []
        image_by_name = {x.get("name"): x for x in manifest.get("images", []) if isinstance(x, dict)}
        for item_meta in manifest.get("items", []):
            entry = image_by_name.get(item_meta.get("name"))
            if not entry: continue
            try:
                img = Image.open(os.path.join(path, entry["file"])).convert("RGB")
                item = self.app.add_image(img, item_meta.get("name", "image"), show=False)
                if item:
                    item.update(kind=item_meta.get("kind", ""), md=item_meta.get("md", ""), raw=item_meta.get("raw", ""), status="done" if item_meta.get("md") else "waiting")
                    loaded.append(item)
            except Exception:
                continue
        self.workspace.vocabulary = [VocabularyEntry(**{**e, "tags": tuple(e.get("tags", ()))}) for e in manifest.get("vocabulary", []) if isinstance(e, dict) and e.get("source")]
        self.workspace.flashcards = [Flashcard(**{**c, "tags": tuple(c.get("tags", ()))}) for c in manifest.get("flashcards", []) if isinstance(c, dict) and c.get("front")]
        self.app.refresh_all(); self.app.sync_editor(); self._refresh_all()
        self.project_info.delete("1.0", "end"); self.project_info.insert("1.0", json.dumps(manifest, ensure_ascii=False, indent=2))
        messagebox.showinfo("Project loaded", f"Loaded {len(loaded)} image(s) and {len(self.workspace.vocabulary)} vocabulary item(s).")


def install(app):
    """Install additive Study Workspace menu and shortcut on the existing App."""
    menu = tk.Menu(app, tearoff=False); study = tk.Menu(menu, tearoff=False)
    study.add_command(label="Open Study Workspace…", command=lambda: StudyWorkspaceWindow(app))
    study.add_command(label="Extract Vocabulary from Current OCR", command=lambda: _quick_extract(app))
    study.add_separator(); study.add_command(label="OCR-to-Learning Workflow", command=lambda: _quick_extract(app))
    menu.add_cascade(label="Study", menu=study); app.configure(menu=menu)
    app.bind("<Control-Shift-V>", lambda e: StudyWorkspaceWindow(app))


def _quick_extract(app):
    win = StudyWorkspaceWindow(app); win.extract_ocr(); win.tabs.set("Vocabulary")
