"""Unified application menu bar and access to the new control centers."""
from __future__ import annotations

import tkinter as tk

from .ai_center import AICenter
from .health_center import HealthCenter
from .settings_center import SettingsCenter


def install(app, study_factory):
    menu = tk.Menu(app, tearoff=False)

    file_menu = tk.Menu(menu, tearoff=False)
    file_menu.add_command(label="Add Images", command=app.add_files)
    file_menu.add_command(label="Add Folder", command=app.add_folder)
    file_menu.add_command(label="Paste Image", command=app.paste)
    file_menu.add_separator(); file_menu.add_command(label="Exit", command=app.destroy)
    menu.add_cascade(label="File", menu=file_menu)

    edit = tk.Menu(menu, tearoff=False)
    edit.add_command(label="Copy All", command=lambda: app.copy(app.combined_text()))
    edit.add_command(label="Copy Original OCR", command=lambda: app.copy(app.combined_text("raw")))
    menu.add_cascade(label="Edit", menu=edit)

    ocr = tk.Menu(menu, tearoff=False)
    ocr.add_command(label="Scan Current", command=app.ocr_current)
    ocr.add_command(label="Scan All — Smart", command=lambda: app.process_all("Smart"))
    ocr.add_command(label="Scan All — Raw", command=lambda: app.process_all("Raw"))
    ocr.add_command(label="Scan All — Deep/Selected Accuracy", command=app.process_all)
    ocr.add_command(label="Cancel OCR", command=app.cancel_ocr)
    menu.add_cascade(label="OCR", menu=ocr)

    ai = tk.Menu(menu, tearoff=False)
    ai.add_command(label="Local AI & Ollama Center…", command=lambda: AICenter(app))
    ai.add_command(label="Local AI Agents…", command=app._open_agents)
    ai.add_command(label="AI Smart All", command=lambda: app.process_all("AI Smart"))
    menu.add_cascade(label="AI", menu=ai)

    batch = tk.Menu(menu, tearoff=False)
    batch.add_command(label="Process Every Image", command=app.process_all)
    batch.add_command(label="Scan All Images", command=lambda: app.process_all("Smart"))
    batch.add_command(label="AI Smart All", command=lambda: app.process_all("AI Smart"))
    batch.add_command(label="Cancel Current Batch", command=app.cancel_ocr)
    menu.add_cascade(label="Batch", menu=batch)

    bot = tk.Menu(menu, tearoff=False)
    bot.add_command(label="OCR Automation Bot…", command=lambda: _open_bot(app))
    menu.add_cascade(label="Bot", menu=bot)

    study = tk.Menu(menu, tearoff=False)
    study.add_command(label="Open Study Workspace…", command=study_factory)
    menu.add_cascade(label="Study", menu=study)

    view = tk.Menu(menu, tearoff=False)
    view.add_command(label="Toggle Editor Focus", command=app.toggle_focus)
    menu.add_cascade(label="View", menu=view)

    tools = tk.Menu(menu, tearoff=False)
    tools.add_command(label="Health Check & Troubleshooting…", command=lambda: HealthCenter(app))
    tools.add_command(label="Open OCR Log", command=lambda: HealthCenter(app).tabs.set("Logs"))
    menu.add_cascade(label="Tools", menu=tools)

    settings = tk.Menu(menu, tearoff=False)
    settings.add_command(label="Settings Center…", command=lambda: SettingsCenter(app))
    settings.add_command(label="Local AI & Ollama…", command=lambda: AICenter(app))
    menu.add_cascade(label="Settings", menu=settings)

    help_menu = tk.Menu(menu, tearoff=False)
    help_menu.add_command(label="Health Check", command=lambda: HealthCenter(app))
    help_menu.add_command(label="Troubleshooting", command=lambda: (lambda w: w.tabs.set("Troubleshooting"))(HealthCenter(app)))
    menu.add_cascade(label="Help", menu=help_menu)

    app.configure(menu=menu)
    app.bind("<Control-Shift-A>", lambda e: AICenter(app))
    app.bind("<Control-Shift-H>", lambda e: HealthCenter(app))
    app.bind("<Control-Shift-S>", lambda e: SettingsCenter(app))


def _open_bot(app):
    from .automation_bot import AutomationBot
    AutomationBot(app)
