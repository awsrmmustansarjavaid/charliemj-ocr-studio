"""Tabbed application settings center."""
from __future__ import annotations

import tkinter as tk
import customtkinter as ctk

from .config import cfg, save_cfg
from .languages import choices, install_pack, install as refresh_languages


class SettingsCenter(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Charlie MJ — Settings")
        self.geometry("800x720")
        self.minsize(680, 580)
        self.vars = {}
        self._build()

    def _choice(self, parent, label, key, values):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=18, pady=(10, 2))
        current = cfg.get(key, values[0] if values else "")
        if key == "title_vocab": current = "Yes" if current else "No"
        var = tk.StringVar(value=str(current)); self.vars[key] = var
        ctk.CTkOptionMenu(parent, variable=var, values=list(values)).pack(fill="x", padx=18)

    def _entry(self, parent, label, key):
        ctk.CTkLabel(parent, text=label).pack(anchor="w", padx=18, pady=(10, 2))
        var = tk.StringVar(value=str(cfg.get(key, ""))); self.vars[key] = var
        ctk.CTkEntry(parent, textvariable=var).pack(fill="x", padx=18)

    def _build(self):
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        general = self.tabs.add("General"); ocr = self.tabs.add("OCR"); langs = self.tabs.add("Languages")
        ai = self.tabs.add("AI / Ollama"); batch = self.tabs.add("Batch"); interface = self.tabs.add("Interface"); storage = self.tabs.add("Storage")
        self._choice(general, "OCR mode", "mode", ["Smart", "Raw", "AI Smart"])
        self._choice(general, "OCR accuracy", "accuracy", ["Fast", "Balanced", "Deep"])
        self._choice(general, "Theme", "theme", ["dark", "light"])
        self._choice(general, "Learner level", "level", ["Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced"])
        self._choice(ocr, "Minimum OCR confidence", "min_conf", [str(x) for x in (20, 30, 40, 45, 55, 65, 75)])
        self._choice(ocr, "Include title as vocabulary", "title_vocab", ["Yes", "No"])
        self.langs = langs
        self._build_language_controls()
        self._entry(ai, "Ollama URL", "ollama_url"); self._entry(ai, "Ollama model", "model")
        self._choice(batch, "Queue policy", "batch_policy", ["Unlimited", "Confirm large imports"])
        self._choice(batch, "Default batch action", "batch_action", ["Smart", "Raw", "AI Smart"])
        self._choice(interface, "Editor auto-update", "editor_auto", ["Yes", "No"])
        ctk.CTkLabel(storage, text="Portable configuration and diagnostics stay beside the executable.", wraplength=650).pack(anchor="w", padx=18, pady=18)
        ctk.CTkButton(storage, text="Open Health & Troubleshooting", command=self.open_health).pack(anchor="w", padx=18, pady=8)
        ctk.CTkButton(self, text="Save All Settings", height=40, command=self.save).pack(pady=(0, 12))

    def _build_language_controls(self):
        for child in self.langs.winfo_children(): child.destroy()
        lang_map = choices(); labels = list(lang_map)
        current_lang = next((k for k, v in lang_map.items() if v == cfg.get("lang")), cfg.get("lang", labels[0] if labels else ""))
        current_native = next((k for k, v in lang_map.items() if v == cfg.get("native")), cfg.get("native", labels[0] if labels else ""))
        self._choice(self.langs, "Learning / OCR language", "lang", labels); self.vars["lang"].set(current_lang)
        self._choice(self.langs, "Translation / native language", "native", labels); self.vars["native"].set(current_native)
        ctk.CTkLabel(self.langs, text=f"Installed Tesseract languages discovered: {len(labels)}", text_color="gray").pack(anchor="w", padx=18, pady=8)
        row = ctk.CTkFrame(self.langs); row.pack(fill="x", padx=18, pady=8)
        ctk.CTkLabel(row, text="Install language code (e.g. deu, fra, jpn):").pack(side="left", padx=6)
        self.pack_code = ctk.CTkEntry(row, width=160); self.pack_code.pack(side="left", padx=6)
        self.pack_status = ctk.CTkLabel(row, text="", text_color="gray"); self.pack_status.pack(side="left", padx=6)
        ctk.CTkButton(row, text="Download official Tesseract pack", command=self.download_pack).pack(side="right", padx=6)

    def download_pack(self):
        code = self.pack_code.get().strip().lower()
        if not code: return self.pack_status.configure(text="Enter a Tesseract code")
        self.pack_status.configure(text=f"Downloading {code}…")
        self.app.bg(lambda: install_pack(code), lambda path: (refresh_languages(), self.pack_status.configure(text=f"✓ Installed: {path}"), self._build_language_controls()),
                    lambda msg: self.pack_status.configure(text=f"✕ {msg[:180]}"))

    def save(self):
        lang_map = choices()
        for key, var in self.vars.items():
            value = var.get()
            if key == "min_conf": value = int(value)
            elif key == "title_vocab": value = value == "Yes"
            elif key in ("lang", "native"):
                value = lang_map.get(value, value)
                friendly = {"tur": "Turkish", "urd": "Urdu", "ara": "Arabic", "fas": "Persian", "eng": "English"}
                value = friendly.get(value, value)
            cfg[key] = value
        save_cfg()
        try:
            self.app.mode.set(cfg.get("mode", "Smart")); self.app.accuracy.set(cfg.get("accuracy", "Balanced")); ctk.set_appearance_mode(cfg.get("theme", "dark")); self.app.refresh_all(); self.app.check_ai()
        except Exception: pass
        self.destroy()

    def open_health(self):
        from .health_center import HealthCenter
        HealthCenter(self.app)
