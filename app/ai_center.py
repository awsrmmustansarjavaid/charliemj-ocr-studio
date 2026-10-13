"""Local AI/Ollama control center.

No cloud service is required.  The center exposes connection diagnostics,
installed models and the local OCR agents already used by the application.
"""
from __future__ import annotations

import customtkinter as ctk

from . import diagnostics, local_agents, local_ai
from .config import cfg, save_cfg


class AICenter(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Charlie MJ — Local AI & Ollama")
        self.geometry("900x680")
        self.minsize(760, 560)
        self._build()
        self.refresh()

    def _build(self):
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.connection = self.tabs.add("Connection")
        self.agents = self.tabs.add("Local Agents")
        self.models = self.tabs.add("Models")
        self._build_connection()
        self._build_agents()
        self._build_models()

    def _build_connection(self):
        form = ctk.CTkFrame(self.connection); form.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(form, text="Ollama URL").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.url = ctk.CTkEntry(form); self.url.grid(row=0, column=1, sticky="ew", padx=8, pady=8); self.url.insert(0, cfg["ollama_url"])
        ctk.CTkLabel(form, text="Model").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        self.model = ctk.CTkComboBox(form, values=[cfg["model"]]); self.model.grid(row=1, column=1, sticky="ew", padx=8, pady=8); self.model.set(cfg["model"])
        form.grid_columnconfigure(1, weight=1)
        row = ctk.CTkFrame(self.connection); row.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(row, text="Save", command=self.save).pack(side="left", padx=4)
        ctk.CTkButton(row, text="Test Connection", command=self.refresh).pack(side="left", padx=4)
        self.status = ctk.CTkLabel(self.connection, text="", anchor="w", justify="left", wraplength=820)
        self.status.pack(fill="x", padx=18, pady=10)
        self.details = ctk.CTkTextbox(self.connection, height=220); self.details.pack(fill="both", expand=True, padx=10, pady=10)

    def _build_agents(self):
        ctk.CTkLabel(self.agents, text="All agents run locally through Ollama.", text_color="gray").pack(anchor="w", padx=12, pady=10)
        self.agent_box = ctk.CTkTextbox(self.agents); self.agent_box.pack(fill="both", expand=True, padx=10, pady=10)
        row = ctk.CTkFrame(self.agents); row.pack(fill="x", padx=10, pady=8)
        for name in local_agents.names():
            ctk.CTkButton(row, text=name, command=lambda n=name: self.run_agent(n)).pack(side="left", padx=3)
        self.agent_output = ctk.CTkTextbox(self.agents, height=180); self.agent_output.pack(fill="x", padx=10, pady=8)

    def _build_models(self):
        self.model_box = ctk.CTkTextbox(self.models); self.model_box.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.models, text="Refresh Models", command=self.refresh).pack(pady=8)

    def save(self):
        cfg["ollama_url"] = self.url.get().strip()
        cfg["model"] = self.model.get().strip()
        save_cfg()
        diagnostics.log("AI", f"saved Ollama URL and model={cfg['model']!r}")
        self.status.configure(text="✓ Saved. Testing connection…")
        self.refresh()

    def refresh(self):
        url = self.url.get().strip() if hasattr(self, "url") else cfg["ollama_url"]
        def done(result):
            ok, names, msg = result
            if names:
                self.model.configure(values=names)
                if cfg["model"] in names:
                    self.model.set(cfg["model"])
            self.status.configure(text=("✓ " if ok else "✕ ") + msg)
            self.model_box.delete("1.0", "end")
            self.model_box.insert("1.0", "\n".join(names) if names else "No models reported by Ollama.")
            self.details.delete("1.0", "end")
            self.details.insert("1.0", f"URL: {url}\nSelected model: {cfg['model']}\nStatus: {msg}\n")
        self.app.bg(lambda: local_ai.status(url), done, lambda msg: self.status.configure(text=f"✕ {msg}"))

    def run_agent(self, name):
        text = self.app.combined_text() if self.app.items else ""
        image = self.app.items[self.app.current]["img"] if self.app.current is not None and self.app.items else None
        if not text and image is None:
            self.status.configure(text="Add or OCR an image first.")
            return
        self.status.configure(text=f"🤖 {name} running…")
        self.app.bg(lambda: local_agents.run(name, text, image),
                    lambda result: (self.agent_output.delete("1.0", "end"), self.agent_output.insert("1.0", result), self.status.configure(text=f"✓ {name} complete")),
                    lambda msg: self.status.configure(text=f"✕ {msg}"))
