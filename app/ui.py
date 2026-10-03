"""
ui.py - the main window of Charlie MJ OCR & Language Studio (v1.2).

Four resizable panels (drag the dividers, or press "◀ Focus" in panel 4):

    1 INPUT        add / screenshot / paste / folder, numbered queue (▲ ▼ to reorder), Process All
    2 PREVIEW      the selected picture, OCR mode switch (Smart | Raw | AI Smart),
                   Extract Text, Select Area, Settings
    3 OCR RESULTS  one card per image: "Image N", thumbnail, editable text, per-image buttons
    4 TEXT EDITOR  formatted study notes built automatically from the results (editor.py)

Data model - every queue entry is a dict called an "item":
    img     PIL image                  name    file name
    status  waiting|working|done|error kind    "smart" | "raw" | "ai" | ""  (which mode produced md)
    md      text shown in the result card (a Markdown table for Smart; editable by the user)
    raw     the plain OCR text         res     layout.Result (Smart mode only) or None
    swap    True when table columns are swapped
    tb      the card's text box (None until the card is drawn)

"Image N" always comes from the item's POSITION in the queue, so the numbers in the cards
AND in the editor renumber automatically when images are removed, added or reordered.

Threading rule: OCR and AI run in worker threads (see App.bg). Workers never touch widgets;
they put callables on a queue that the UI thread empties every 50 ms (App.poll).
"""
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageGrab, ImageTk

from . import __version__, layout, local_ai, ocr_engine, prompts
from . import richtext as rt
from .config import EXTS, ICON, LANGS, cfg, save_cfg
from .editor import RichEditor
from .selector import AreaSelector

MODES = ["Smart", "Raw", "AI Smart"]
PURPLE = {"fg_color": "#6b46c1", "hover_color": "#805ad5"}      # style of AI buttons
GRAY = {"fg_color": "gray30"}


class App(ctk.CTk):
    """The application window."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(cfg["theme"])
        ctk.set_default_color_theme("blue")
        self.title(f"Charlie MJ OCR & Language Studio  v{__version__}")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{min(1760, sw - 40)}x{min(900, sh - 80)}+10+10")
        self.minsize(900, 560)

        self.items, self.removed, self.current, self.active = [], [], None, None
        self.focus_mode = False
        self.mode = tk.StringVar(value=cfg["mode"] if cfg["mode"] in MODES else "Smart")
        self.blank = ctk.CTkImage(Image.new("RGBA", (1, 1)), size=(1, 1))   # "empty" image for labels
        self._q = queue.Queue()                                              # worker -> UI thread

        # status bar (packed first so it stays at the bottom)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=10, pady=3)
        self.status_lbl = ctk.CTkLabel(bar, text="✓ Ready", anchor="w")
        self.status_lbl.pack(side="left")
        self.ai_lbl = ctk.CTkLabel(bar, text="AI: checking…", anchor="e", text_color="gray")
        self.ai_lbl.pack(side="right")

        # the four panels live in a PanedWindow, so the user can drag the dividers
        dark = ctk.get_appearance_mode() == "Dark"
        self.panes = tk.PanedWindow(self, orient="horizontal", sashwidth=8, sashrelief="flat", bd=0,
                                    bg="#111111" if dark else "#c8c8c8")
        self.panes.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.pq, self.pp, self.pr, self.pe = (ctk.CTkFrame(self.panes) for _ in range(4))
        self.panes.add(self.pq, width=270, minsize=210, stretch="never")
        self.panes.add(self.pp, width=280, minsize=220, stretch="never")
        self.panes.add(self.pr, width=470, minsize=300, stretch="always")
        self.panes.add(self.pe, width=620, minsize=420, stretch="always")
        self.build_queue(self.pq)
        self.build_preview(self.pp)
        self.build_results(self.pr)
        self.build_editor(self.pe)

        self.bind("<Control-v>", self._ctrl_v)
        self.refresh_all()
        self.poll()
        self.check_ai()

    # ================================================================ construction
    def build_queue(self, p):
        """Panel 1: input buttons, batch counter, numbered queue, remove / process buttons."""
        ctk.CTkLabel(p, text="📥 INPUT", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        for txt, cmd in [("＋ Add Images", self.add_files), ("📸 Screenshot", self.snip),
                         ("📋 Paste Image", self.paste), ("📂 Add Folder", self.add_folder)]:
            ctk.CTkButton(p, text=txt, command=cmd).pack(fill="x", padx=10, pady=2)
        self.count = ctk.CTkLabel(p, text="")
        self.count.pack(pady=(8, 0))
        self.list = ctk.CTkScrollableFrame(p)
        self.list.pack(fill="both", expand=True, padx=6, pady=6)
        r = ctk.CTkFrame(p, fg_color="transparent")
        r.pack(fill="x", padx=6)
        for txt, cmd in [("🗑 Selected", self.remove_sel), ("🗑 All", self.remove_all), ("↶ Undo", self.undo_remove)]:
            ctk.CTkButton(r, text=txt, width=72, fg_color="#7a2e2e", hover_color="#a03a3a", command=cmd).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(p, text="⚡ Process All", height=38, command=self.process_all).pack(fill="x", padx=10, pady=8)

    def build_preview(self, p):
        """Panel 2: preview, OCR mode switch, per-image OCR buttons."""
        ctk.CTkLabel(p, text="🖼 PREVIEW", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        self.prev = ctk.CTkLabel(p, text="No image selected")
        self.prev.pack(expand=True, fill="both", padx=8)
        self.prev.bind("<Double-Button-1>", lambda e: self.select_area())
        ctk.CTkLabel(p, text="OCR mode", text_color="gray").pack()
        ctk.CTkSegmentedButton(p, values=MODES, variable=self.mode,
                               command=lambda v: (cfg.update(mode=v), save_cfg())).pack(pady=(0, 2))
        for line in ("Smart: finds the structure → table, title",
                     "Raw: all text exactly as found, nothing removed",
                     "AI Smart: local AI writes title, headings, bullets"):
            ctk.CTkLabel(p, text=line, text_color="gray", font=("Segoe UI", 10), wraplength=250).pack()
        r = ctk.CTkFrame(p, fg_color="transparent")
        r.pack(pady=(8, 2))
        ctk.CTkButton(r, text="🔍 Extract Text", width=118, command=self.ocr_current).pack(side="left", padx=3)
        ctk.CTkButton(r, text="✂ Select Area", width=118, command=self.select_area, **PURPLE).pack(side="left", padx=3)
        ctk.CTkButton(p, text="⚙ Settings", command=self.settings, **GRAY).pack(pady=(2, 10))

    def build_results(self, p):
        """Panel 3: one card per image + buttons that copy all results."""
        ctk.CTkLabel(p, text="📄 OCR RESULTS", font=("Segoe UI", 14, "bold")).pack(pady=(10, 2))
        self.results = ctk.CTkScrollableFrame(p)
        self.results.pack(fill="both", expand=True, padx=6, pady=4)
        f = ctk.CTkFrame(p, fg_color="transparent")
        f.pack(padx=6, pady=(2, 8))
        specs = [("Copy Selected", self.copy_sel), ("Copy All", lambda: self.copy(self.combined_text())),
                 ("Copy Plain", lambda: self.copy(layout.to_plain(self.combined_text()))),
                 ("Copy Original OCR", lambda: self.copy(self.combined_text("raw"))),
                 ("🧩 Combine → Editor", lambda: self.sync_editor(True)), ("Clear", self.clear_all)]
        for i, (txt, cmd) in enumerate(specs):
            ctk.CTkButton(f, text=txt, width=128, height=28, command=cmd).grid(row=i // 3, column=i % 3, padx=2, pady=2)

    def build_editor(self, p):
        """Panel 4: the formatted text editor."""
        ctk.CTkLabel(p, text="📝 TEXT EDITOR", font=("Segoe UI", 14, "bold")).pack(pady=(10, 0))
        self.editor = RichEditor(p, ai_names=list(prompts.ACTIONS), on_ai=self.ai_action,
                                 on_update=lambda: self.sync_editor(True), on_focus=self.toggle_focus, status=self.status)
        self.editor.pack(fill="both", expand=True)

    def toggle_focus(self):
        """Hide panels 1-3 so the editor fills the window (and bring them back)."""
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            for f in (self.pq, self.pp, self.pr):
                self.panes.forget(f)
        else:
            for f, w, m in ((self.pq, 270, 210), (self.pp, 280, 220), (self.pr, 470, 300)):
                self.panes.add(f, before=self.pe, width=w, minsize=m, stretch="never")

    # ================================================================ helpers
    def status(self, t):
        self.status_lbl.configure(text=t)

    def post(self, fn):
        """Called from worker threads: run fn on the UI thread."""
        self._q.put(fn)

    def poll(self):
        """UI thread: run everything the workers queued, then check again in 50 ms."""
        try:
            while True:
                self._q.get_nowait()()
        except queue.Empty:
            pass
        except Exception as e:                                # a bad callback must never stop the loop
            self.status(f"⚠ {e}")
        self.after(50, self.poll)

    def bg(self, fn, done, fail=None):
        """Run fn() in a worker thread, then done(result) on the UI thread (errors -> status bar / fail)."""
        def work():
            try:
                res = fn()
            except Exception as e:
                msg = str(e) or e.__class__.__name__
                self.post(lambda: (fail(msg) if fail else None, self.status(f"⚠ {msg[:200]}")))
            else:
                self.post(lambda: done(res))
        threading.Thread(target=work, daemon=True).start()

    def check_ai(self):
        """Show in the status bar whether the optional local AI (Ollama) is reachable."""
        def done(r):
            ok, models, msg = r
            self.ai_lbl.configure(text=f"AI: ✓ {cfg['model']}" if ok and cfg["model"] in models else f"AI: ● {msg[:70]}")
        self.bg(lambda: local_ai.status(cfg["ollama_url"]), done)

    def copy(self, t):
        self.clipboard_clear()
        self.clipboard_append(t)
        self.status("✓ Copied to clipboard")

    def copy_sel(self):
        try:
            self.copy(self.active.get("sel.first", "sel.last"))
        except (tk.TclError, AttributeError):
            self.status("Select some text in a result card first")

    def _ctrl_v(self, e):
        if not isinstance(self.focus_get(), (tk.Text, tk.Entry)):
            self.paste()

    # ================================================================ queue
    def new_item(self, img, name):
        th = img.copy()
        th.thumbnail((90, 60))
        return {"img": img, "name": name, "status": "waiting", "th": th, "sel": tk.BooleanVar(), "md": "",
                "raw": "", "res": None, "swap": False, "kind": "", "tb": None, "rendered": ""}

    def add_image(self, img, name, at=None, show=True):
        """Add an image (at the end, or at index `at`). Returns the item, or None at the batch limit."""
        if len(self.items) >= cfg["batch_limit"]:
            messagebox.showwarning("Batch limit reached", f"Limit is {cfg['batch_limit']}. Remove an image or change it in Settings.")
            return None
        self.save_cards()
        it = self.new_item(img, name)
        self.items.insert(len(self.items) if at is None else at, it)
        self.refresh_all()
        if show:
            self.show(self.items.index(it))
        return it

    def open_path(self, path):
        """Add an image file to the queue."""
        return self.add_image(Image.open(path).convert("RGB"), os.path.basename(path))

    def refresh_all(self):
        self.refresh_queue()
        self.refresh_results()

    def refresh_queue(self):
        """Redraw the numbered queue cards (cheap: no text boxes)."""
        for w in self.list.winfo_children():
            w.destroy()
        for i, it in enumerate(self.items):
            f = ctk.CTkFrame(self.list)
            f.pack(fill="x", pady=3)
            ctk.CTkCheckBox(f, text="", width=22, variable=it["sel"]).pack(side="left", padx=3)
            lb = ctk.CTkLabel(f, text="", image=ctk.CTkImage(it["th"], size=it["th"].size))
            lb.pack(side="left")
            info = ctk.CTkLabel(f, text=f"{i + 1}. {it['name'][:13]}\n{ICON[it['status']]}", justify="left", anchor="w")
            info.pack(side="left", padx=5)
            mv = ctk.CTkFrame(f, fg_color="transparent")
            mv.pack(side="right", padx=2)
            ctk.CTkButton(mv, text="▲", width=24, height=20, command=lambda i=i: self.move(i, -1), **GRAY).pack()
            ctk.CTkButton(mv, text="▼", width=24, height=20, command=lambda i=i: self.move(i, 1), **GRAY).pack(pady=1)
            for w in (f, lb, info):
                w.bind("<Button-1>", lambda e, i=i: self.show(i))
        self.count.configure(text=f"Batch: {len(self.items)} / {cfg['batch_limit']}")

    def move(self, i, d):
        """Move an image up / down; 'Image N' numbers follow automatically."""
        j = i + d
        if 0 <= j < len(self.items):
            self.save_cards()
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.refresh_all()
            self.sync_editor()

    def show(self, i):
        """Preview queue item i."""
        self.current = i
        img = self.items[i]["img"].copy()
        img.thumbnail((250, 360))
        self.prev.configure(image=ctk.CTkImage(img, size=img.size), text="")

    def clear_preview(self):
        self.current = None
        self.prev.configure(image=self.blank, text="No image selected")

    def remove_items(self, gone):
        """Remove items (kept for Undo), renumber, and update the editor."""
        if not gone:
            return
        self.save_cards()
        self.removed = [(self.items.index(it), it) for it in gone]
        self.items = [it for it in self.items if it not in gone]
        self.clear_preview()
        self.refresh_all()
        self.sync_editor()

    def remove_sel(self):
        gone = [it for it in self.items if it["sel"].get()]
        if not gone and self.current is not None:
            gone = [self.items[self.current]]
        self.remove_items(gone)

    def remove_all(self):
        if self.items and messagebox.askyesno("Remove all", "Remove all images from the queue?"):
            self.remove_items(list(self.items))

    def undo_remove(self):
        """Put the last removed images back in their old positions."""
        for i, it in sorted(self.removed, key=lambda x: x[0]):
            if len(self.items) < cfg["batch_limit"]:
                self.items.insert(min(i, len(self.items)), it)
        self.removed = []
        self.refresh_all()
        self.sync_editor()

    def add_files(self):
        for f in filedialog.askopenfilenames(filetypes=[("Images", " ".join("*" + e for e in EXTS))]):
            if not self.open_path(f):
                break

    def add_folder(self):
        d = filedialog.askdirectory()
        for f in sorted(os.listdir(d)) if d else []:
            if f.lower().endswith(EXTS) and not self.open_path(os.path.join(d, f)):
                break

    def paste(self):
        c = ImageGrab.grabclipboard()
        if isinstance(c, Image.Image):
            self.add_image(c.convert("RGB"), "pasted.png")
        elif isinstance(c, list):
            for f in c:
                if f.lower().endswith(EXTS):
                    self.open_path(f)
        else:
            self.status("No image in the clipboard")

    # ---------------------------------------------------------------- screenshot
    def snip(self):
        """Hide the window, then drag a rectangle on a frozen screenshot."""
        self.withdraw()
        self.after(350, self._snip)

    def _snip(self):
        shot = ImageGrab.grab()
        top = tk.Toplevel()
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        photo = ImageTk.PhotoImage(shot.resize((sw, sh)))
        cv = tk.Canvas(top, cursor="cross", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cv.create_image(0, 0, image=photo, anchor="nw")
        cv.image = photo                                     # keep a reference alive
        st = {}

        def down(e):
            st["x"], st["y"] = e.x, e.y
            st["r"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2)

        def move(e):
            if "r" in st:
                cv.coords(st["r"], st["x"], st["y"], e.x, e.y)

        def up(e):
            k = shot.width / sw
            x1, x2 = sorted((st.get("x", 0), e.x))
            y1, y2 = sorted((st.get("y", 0), e.y))
            top.destroy()
            self.deiconify()
            if x2 - x1 > 5 and y2 - y1 > 5:
                self.add_image(shot.crop((int(x1 * k), int(y1 * k), int(x2 * k), int(y2 * k))).convert("RGB"), "screenshot.png")

        def cancel(e=None):
            top.destroy()
            self.deiconify()
        cv.bind("<ButtonPress-1>", down)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", up)
        top.bind("<Escape>", cancel)

    # ---------------------------------------------------------------- select area
    def select_area(self, it=None):
        """Open the Select Area window for an image (default: the previewed one)."""
        if it is None:
            if self.current is None:
                return self.status("Select an image first")
            it = self.items[self.current]
        AreaSelector(self, it["img"], lambda crop, n: self.add_area(it, crop, n))

    def add_area(self, src, crop, n):
        """A selected box becomes a new image right after its source and is OCR'd at once."""
        at = self.items.index(src) + 1 if src in self.items else len(self.items)
        stem = os.path.splitext(src["name"])[0]
        new = self.add_image(crop, f"{stem} · area {n}", at=at, show=False)
        if new:
            self.run_ocr(new, self.mode.get())
        return new

    # ================================================================ result cards (panel 3)
    def save_cards(self):
        """Copy text the user TYPED in a card back into its item (the item is the source of truth)."""
        for it in self.items:
            if it.get("tb") is not None:
                try:
                    cur = it["tb"].get("1.0", "end-1c")
                except tk.TclError:
                    continue
                if cur != it["rendered"]:            # only if the USER typed: programmatic changes to it["md"] must survive
                    it["md"] = it["rendered"] = cur

    def refresh_results(self):
        """Redraw one card per image: 'Image N', thumbnail, buttons, editable text, break line."""
        self.save_cards()
        for w in self.results.winfo_children():
            w.destroy()
        self.active = None
        for i, it in enumerate(self.items):
            card = ctk.CTkFrame(self.results, fg_color="transparent")
            card.pack(fill="x")
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x")
            ctk.CTkLabel(head, text="", image=ctk.CTkImage(it["th"], size=it["th"].size)).pack(side="left")
            ctk.CTkLabel(head, text=f"Image {i + 1}", font=("Segoe UI", 20, "bold")).pack(side="left", padx=10)
            ctk.CTkLabel(head, text=f"{it['name'][:30]}\n{ICON[it['status']]}", text_color="gray", justify="left", anchor="w").pack(side="left")
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", pady=(2, 0))
            for txt, cmd in [("Copy", lambda it=it: self.copy_item(it)), ("↻ Smart", lambda it=it: self.run_ocr(it, "Smart")),
                             ("↻ Raw", lambda it=it: self.run_ocr(it, "Raw")), ("↻ AI", lambda it=it: self.run_ocr(it, "AI Smart")),
                             ("⇄ Swap", lambda it=it: self.swap(it)), ("✂ Area", lambda it=it: self.select_area(it)),
                             ("🗑", lambda it=it: self.remove_items([it]))]:
                ctk.CTkButton(row, text=txt, width=50, height=26, command=cmd, **GRAY).pack(side="left", padx=1)
            tb = ctk.CTkTextbox(card, height=190, undo=True, font=("Consolas", 13), wrap="none")
            tb.pack(fill="x", pady=4)
            tb.insert("1.0", it["md"])
            it["rendered"] = it["md"]
            tb.bind("<FocusIn>", lambda e, t=tb: setattr(self, "active", t))
            it["tb"] = tb
            ctk.CTkFrame(self.results, height=3, fg_color="gray40").pack(fill="x", pady=10)     # break line between images

    def copy_item(self, it):
        self.save_cards()
        self.copy(it["md"])

    def swap(self, it):
        """Swap the two table columns of one image."""
        self.save_cards()
        if it["res"] is None or it["res"].kind != "bilingual":
            return self.status("Swap works on bilingual tables from Smart OCR")
        it["swap"] = not it["swap"]
        it["md"] = layout.to_markdown(it["res"], cfg["lang"], cfg["native"], it["swap"])
        self.refresh_results()
        self.sync_editor()

    def combined_text(self, field="md"):
        """All images in order: '## Image N', file name, text - separated by a horizontal line."""
        self.save_cards()
        parts = [f"## Image {i}\n*{it['name']}*\n\n{(it[field] or '').strip()}"
                 for i, it in enumerate(self.items, 1) if (it[field] or "").strip()]
        return "\n\n---\n\n".join(parts)

    def clear_all(self):
        if self.items and messagebox.askyesno("Clear", "Clear the OCR text of ALL images? (the images stay in the queue)"):
            for it in self.items:
                it.update(md="", raw="", res=None, swap=False, kind="", status="waiting")
            self.refresh_all()
            self.sync_editor()

    # ================================================================ OCR (three modes)
    def codes(self):
        """(full Tesseract code, learning-language code, translation-language code), e.g. ('tur+eng','tur','eng')."""
        full = LANGS[cfg["lang"]]
        return full, full.split("+")[0], LANGS.get(cfg["native"], "eng").split("+")[0]

    def ai_smart(self, img, hint):
        """Ask the local model for structured notes. Falls back to text-only if the model cannot see images."""
        prompt = prompts.ai_smart(hint)
        try:
            return local_ai.generate(cfg["ollama_url"], cfg["model"], prompt, img)
        except RuntimeError as e:
            if any(w in str(e).lower() for w in ("image", "vision", "multimodal")):
                return local_ai.generate(cfg["ollama_url"], cfg["model"], prompt)
            raise

    def read(self, it, mode):
        """Worker thread: run OCR in `mode`. Returns (mode, output, warning)."""
        code, c1, c2 = self.codes()
        if mode == "Raw":
            return "Raw", ocr_engine.read_raw(it["img"], code), None
        words, g = ocr_engine.read_words(it["img"], code)
        res = layout.analyze(words, cfg["lang"], cfg["min_conf"], ocr_engine.make_refiner(g, c1, c2),
                             ocr_engine.make_cell_reader(g, code))
        if mode == "Smart":
            return "Smart", res, None
        hint = (layout.to_markdown(res, cfg["lang"], cfg["native"]) if res.kind == "bilingual" else res.raw)
        try:
            return "AI Smart", self.ai_smart(it["img"], hint + "\n\nAll OCR lines:\n" + res.raw), None
        except Exception as e:                                # no AI available -> still give the Smart result
            return "Smart", res, str(e) or e.__class__.__name__

    def apply(self, it, mode, out, warn=None):
        """Store an OCR result in its item; returns a one-line summary for the status bar."""
        if mode == "Raw":
            it.update(kind="raw", raw=out, res=None, swap=False, md=re.sub(r"\n{3,}", "\n\n", out).strip())
            info = "Raw text (every word)"
        elif mode == "Smart":
            it.update(kind="smart", res=out, raw=out.raw, swap=False, md=layout.to_markdown(out, cfg["lang"], cfg["native"]))
            info = layout.status_line(out, cfg["lang"], cfg["native"])
            if warn:
                info = f"⚠ AI Smart unavailable ({warn[:80]}) – showing the Smart result. " + info
        else:
            it.update(kind="ai", res=None, swap=False, md=out.strip())
            info = "AI Smart notes – please double-check them"
        it["status"] = "done"
        return info

    def run_ocr(self, it, mode):
        """OCR one image in the given mode, then update its card and the editor."""
        self.save_cards()
        it["status"] = "working"
        self.refresh_queue()
        if mode == "AI Smart":
            self.status("🤖 AI Smart is reading the picture… (local AI can take a minute)")

        def done(r):
            info = self.apply(it, *r)
            self.refresh_all()
            self.sync_editor()
            self.status("✓ " + info if not info.startswith("⚠") else info)

        def fail(msg):
            it["status"] = "error"
            self.refresh_queue()
        self.bg(lambda: self.read(it, mode), done, fail)

    def ocr_current(self):
        if self.current is None:
            return self.status("Select an image first")
        self.run_ocr(self.items[self.current], self.mode.get())

    def process_all(self):
        """OCR every unfinished image, one after another, in the chosen mode."""
        todo = [it for it in self.items if it["status"] != "done"]
        mode = self.mode.get()
        if not todo:
            return self.status("Nothing to process")
        self.save_cards()

        def run():
            for n, it in enumerate(todo, 1):
                self.post(lambda it=it, n=n: (it.update(status="working"), self.refresh_queue(),
                                              self.status(f"Processing {n} / {len(todo)} ({mode})…")))
                try:
                    r, ok = self.read(it, mode), True
                except Exception:
                    r, ok = None, False                       # mark this image as error, go on with the rest
                self.post(lambda it=it, r=r, ok=ok: (self.apply(it, *r) if ok else it.update(status="error"), self.refresh_queue()))
            self.post(lambda: (self.refresh_all(), self.sync_editor(), self.status(f"✓ Finished {len(todo)} image(s)")))
        threading.Thread(target=run, daemon=True).start()

    # ================================================================ editor sync + AI buttons
    def notes_md(self, it):
        """Study-notes Markdown of one image for the editor (headings + bullets by default)."""
        md = (it["md"] or "").strip()
        if not md:
            return ""
        if it["kind"] == "ai":
            return md
        if it["kind"] == "smart":
            return layout.to_notes(it["res"], md)
        if it["kind"] == "raw":
            return layout.text_notes(md, "Raw text")
        return md

    def editor_blocks(self):
        """Whole editor document: for each image 'Image N' (title), file name, notes, separator line."""
        self.save_cards()
        out = []
        for i, it in enumerate(self.items, 1):
            notes = self.notes_md(it)
            if notes:
                out += [rt.Block("title", runs=[rt.Run(f"Image {i}")]),
                        rt.Block(runs=[rt.Run(it["name"], italic=True, size=10, color="#888888")])]
                out += rt.md_to_blocks(notes, top="h1")
                out.append(rt.Block(hr=True))
        return out

    def sync_editor(self, force=False):
        """Rebuild the editor from the OCR results.

        Automatic updates never overwrite text the user edited (editor.dirty); the user can
        still force it with '⟳ Update from OCR' / 'Combine → Editor' (and undo it with '⤺ Restore').
        """
        ed = self.editor
        if force:
            if ed.dirty and not messagebox.askyesno("Update editor", "Replace the text in the editor with the current OCR results?\n"
                                                    "(You can bring your text back with ⤺ Restore.)"):
                return
        elif ed.dirty:
            return self.status("✎ The editor has your edits – press ⟳ Update from OCR to rebuild it")
        elif not ed.auto.get():
            return
        ed.load_blocks(self.editor_blocks())

    def ai_action(self, name):
        """Run an AI button on the selected editor lines (or the whole editor)."""
        text, lines = self.editor.selection_text()
        if not text.strip():
            return self.status("The editor is empty – nothing to send to the AI")
        build, mode = prompts.ACTIONS[name]
        self.status(f"🤖 {name} (local AI, please wait)…")

        def done(res):
            self.editor.apply_ai(res, mode, lines)
            self.status(f"✓ {name} done – please double-check")
        self.bg(lambda: local_ai.generate(cfg["ollama_url"], cfg["model"], build(text)), done)

    # ================================================================ settings
    def settings(self):
        """Modal settings window with a local-AI connection test."""
        w = ctk.CTkToplevel(self)
        w.title("Settings")
        w.geometry("440x680")
        w.grab_set()
        v = {}

        def row(label, key, values=None, combo=False):
            ctk.CTkLabel(w, text=label).pack(anchor="w", padx=20, pady=(8, 0))
            v[key] = tk.StringVar(value=str(cfg[key]))
            if combo:
                box = ctk.CTkComboBox(w, variable=v[key], values=values or [])
            else:
                box = ctk.CTkOptionMenu(w, variable=v[key], values=values) if values else ctk.CTkEntry(w, textvariable=v[key])
            box.pack(fill="x", padx=20)
            return box
        row("Learning language (OCR + first table column)", "lang", list(LANGS))
        row("Your language (second column / AI answers)", "native", ["English", "Urdu", "Turkish", "Arabic", "Persian"])
        row("Level", "level", ["Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced"])
        row("Image batch limit", "batch_limit", ["5", "10", "20", "50", "100"])
        row("Ignore OCR text below this confidence (0-100)", "min_conf", ["30", "40", "45", "55", "65", "75"])
        row("Theme (restart to apply fully)", "theme", ["dark", "light"])
        ctk.CTkLabel(w, text="── Local AI (Ollama) ──", text_color="gray").pack(pady=(14, 0))
        row("Ollama address (localhost only)", "ollama_url")
        models = row("Model", "model", [cfg["model"]], combo=True)
        result = ctk.CTkLabel(w, text="", wraplength=380, justify="left")

        def test():
            result.configure(text="Testing…")
            url = v["ollama_url"].get().strip()

            def done(r):
                ok, names, msg = r
                if names:
                    models.configure(values=names)
                result.configure(text=("✓ " if ok else "✕ ") + msg, text_color="#4ade80" if ok else "#f87171")
            self.bg(lambda: local_ai.status(url), done)
        ctk.CTkButton(w, text="Test AI connection", command=test, **GRAY).pack(pady=8)
        result.pack(padx=20)

        def save():
            for k, var in v.items():
                cfg[k] = int(var.get()) if k in ("batch_limit", "min_conf") else var.get().strip()
            save_cfg()
            ctk.set_appearance_mode(cfg["theme"])
            self.refresh_all()
            self.check_ai()
            w.destroy()
        ctk.CTkButton(w, text="Save Settings", command=save).pack(pady=14)
