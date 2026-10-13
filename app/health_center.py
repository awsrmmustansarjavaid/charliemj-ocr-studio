"""Health Check and Troubleshooting center."""
from __future__ import annotations

import os
import shutil
import subprocess
import tkinter as tk
import customtkinter as ctk

from . import diagnostics, local_ai
from .config import BASE, cfg
from .languages import installed_codes


class HealthCenter(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Charlie MJ — Health Check & Troubleshooting")
        self.geometry("900x680")
        self.tabs = ctk.CTkTabview(self); self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.health = self.tabs.add("Health Check")
        self.logs = self.tabs.add("Logs")
        self.help = self.tabs.add("Troubleshooting")
        self._build_health(); self._build_logs(); self._build_help(); self.run_checks()

    def _build_health(self):
        row = ctk.CTkFrame(self.health); row.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(row, text="Run Health Check", command=self.run_checks).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Open Log", command=lambda: self.tabs.set("Logs")).pack(side="left", padx=4)
        self.health_box = ctk.CTkTextbox(self.health); self.health_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_logs(self):
        row = ctk.CTkFrame(self.logs); row.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(row, text="Refresh", command=self.refresh_logs).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Clear Log", command=lambda: (diagnostics.clear(), self.refresh_logs())).pack(side="left", padx=4)
        self.log_box = ctk.CTkTextbox(self.logs, font=("Consolas", 11)); self.log_box.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_help(self):
        text = (
            "If Smart/AI stays on Working:\n"
            "1. Open Health Check and confirm Tesseract + language data are available.\n"
            "2. Open Logs and look for OCR-START, OCR-WORKER, OCR-APPLY or OCR-ERROR.\n"
            "3. Retry the affected image; each image is now an independent job.\n\n"
            "If AI says Ollama is not running:\n"
            "• Start Ollama and confirm the configured URL.\n"
            "• Open Local AI & Ollama → Connection → Test Connection.\n"
            "• Confirm the selected model is installed.\n\n"
            "If a language is missing:\n"
            "• Install its Tesseract traineddata, then restart the app.\n"
            "• The Languages tab discovers installed Tesseract codes automatically.\n"
        )
        self.help_box = ctk.CTkTextbox(self.help); self.help_box.pack(fill="both", expand=True, padx=10, pady=10); self.help_box.insert("1.0", text)

    def run_checks(self):
        self.health_box.delete("1.0", "end")
        self.health_box.insert("end", "Running local checks…\n")
        self.app.bg(self._check_all, self._show_checks, lambda msg: self._show_checks({"Health check": f"ERROR: {msg}"}))

    def _check_all(self):
        checks = {}
        checks["Application"] = "OK"
        tess = os.path.join(BASE, "tesseract", "tesseract.exe")
        checks["Bundled Tesseract"] = "OK: " + tess if os.path.exists(tess) else "NOT FOUND (system Tesseract may still be available)"
        checks["OCR languages"] = f"OK: {len(installed_codes())} installed — {', '.join(installed_codes()[:40])}"
        checks["Storage"] = "OK: writable" if os.access(BASE, os.W_OK) else "WARNING: application folder is not writable"
        try:
            ok, names, msg = local_ai.status(cfg["ollama_url"])
            checks["Ollama"] = ("OK: " if ok else "NOT AVAILABLE: ") + msg + (f" | models={len(names)}" if names else "")
        except Exception as exc:
            checks["Ollama"] = f"ERROR: {exc}"
        checks["Log"] = diagnostics.LOG_PATH
        return checks

    def _show_checks(self, checks):
        self.health_box.delete("1.0", "end")
        for name, result in checks.items():
            self.health_box.insert("end", f"{name}: {result}\n")
        self.refresh_logs()

    def refresh_logs(self):
        self.log_box.delete("1.0", "end"); self.log_box.insert("1.0", diagnostics.recent())
