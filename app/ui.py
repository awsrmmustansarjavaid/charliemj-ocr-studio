"""
ui.py - the main window of Charlie MJ OCR & Language Studio (v1.3).

Four resizable panels (drag the dividers, or press "◀ Focus" in the editor toolbar):

    1 INPUT        add / screenshot / paste / folder, numbered queue (▲ ▼ to reorder), Process All
    2 PREVIEW      the selected picture, OCR mode (Smart | Raw | AI Smart), accuracy (Fast | Balanced |
                   Deep), Extract Text, Select Area, Settings
    3 OCR RESULTS  one card per image: "Image N", thumbnail, editable text, captured areas
    4 TEXT EDITOR  formatted study notes built automatically from the results (editor.py)

Data model - every queue entry is a dict called an "item" (a record):
    img     PIL image                  name    file name
    status  waiting|working|done|error kind    "smart" | "raw" | "ai" | ""  (which mode produced md)
    md      text shown in the result card (a Markdown table for Smart; editable by the user)
    raw     the plain OCR text         res     layout.Result (Smart mode only) or None
    swap    True when the table columns are swapped
    areas   captured areas: records of the same shape (with "parent" and "n"). A box drawn with the
            Select Area tool is OCR'd and ADDED here, so it belongs to the image it was taken from
            and does not use up a slot of the batch limit.

"Image N" always comes from the item's POSITION in the queue, so the numbers in the cards AND in the
editor renumber automatically when images are removed, added or reordered.

Threading rule: OCR and AI run in worker threads (see App.bg). Workers never touch widgets; they put
callables on a queue that the UI thread empties every 50 ms (App.poll).
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
from .widgets import FlowFrame

MODES = ["Smart", "Raw", "AI Smart"]
ACCURACY = ["Fast", "Balanced", "Deep"]
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
        W, H = min(1760, sw - 40), min(900, sh - 80)
        self.geometry(f"{W}x{H}+10+10")
        self.minsize(900, 560)

        self.items, self.removed, self.current, self.active = [], [], None, None
        self.focus_mode = False
        self.mode = tk.StringVar(value=cfg["mode"] if cfg["mode"] in MODES else "Smart")
        self.accuracy = tk.StringVar(value=cfg["accuracy"] if cfg["accuracy"] in ACCURACY else "Balanced")
        self.blank = ctk.CTkImage(Image.new("RGBA", (1, 1)), size=(1, 1))   # "empty" image for labels
        self._q = queue.Queue()                                              # worker -> UI thread

        # status bar (packed first so it stays at the bottom)
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.pack(side="bottom", fill="x", padx=10, pady=3)
        self.status_lbl = ctk.CTkLabel(bar, text="✓ Ready", anchor="w")
        self.status_lbl.pack(side="left")
        self.ai_lbl = ctk.CTkLabel(bar, text="AI: checking…", anchor="e", text_color="gray")
        self.ai_lbl.pack(side="right")
        self.progress = ctk.CTkProgressBar(bar, width=150)                  # shown only while a batch runs
        self.progress.set(0)

        # the four panels live in a PanedWindow, so the user can drag the dividers; the widths follow the screen
        dark = ctk.get_appearance_mode() == "Dark"
        self.panes = tk.PanedWindow(self, orient="horizontal", sashwidth=8, sashrelief="flat", bd=0,
                                    bg="#111111" if dark else "#c8c8c8")
        self.panes.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.pq, self.pp, self.pr, self.pe = (ctk.CTkFrame(self.panes) for _ in range(4))
        self.pane_sizes = ((self.pq, max(190, int(W * .14)), 170), (self.pp, max(210, int(W * .15)), 190),
                           (self.pr, max(300, int(W * .27)), 260))
        for f, w, m in self.pane_sizes:
            self.panes.add(f, width=w, minsize=m, stretch="never")
        self.panes.add(self.pe, minsize=360, stretch="always")
        self.build_queue(self.pq)
        self.build_preview(self.pp)
        self.build_results(self.pr)
        self.build_editor(self.pe)

        self.bind("<Control-v>", self._ctrl_v)
        self.bind("<Control-o>", lambda e: self.add_files())
        self.bind("<F5>", lambda e: self.process_all())
        self.bind("<Control-Return>", lambda e: self.ocr_current())
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
        r = FlowFrame(p)
        r.pack(fill="x", padx=4)
        for txt, cmd in [("🗑 Selected", self.remove_sel), ("🗑 All", self.remove_all), ("↶ Undo", self.undo_remove)]:
            r.add(ctk.CTkButton(r, text=txt, width=70, fg_color="#7a2e2e", hover_color="#a03a3a", command=cmd))
        ctk.CTkButton(p, text="⚡ Process All  (F5)", height=38, command=self.process_all).pack(fill="x", padx=10, pady=8)

    def build_preview(self, p):
        """Panel 2: preview, OCR mode + accuracy switches, per-image OCR buttons."""
        ctk.CTkLabel(p, text="🖼 PREVIEW", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        self.prev = ctk.CTkLabel(p, text="No image selected")
        self.prev.pack(expand=True, fill="both", padx=8)
        self.prev.bind("<Double-Button-1>", lambda e: self.select_area())
        ctk.CTkLabel(p, text="OCR mode", text_color="gray").pack()
        ctk.CTkSegmentedButton(p, values=MODES, variable=self.mode,
                               command=lambda v: (cfg.update(mode=v), save_cfg())).pack(pady=(0, 2))
        for line in ("Smart: finds the structure → table, title",
                     "Raw: the complete text, nothing removed",
                     "AI Smart: local AI writes title, headings, bullets"):
            ctk.CTkLabel(p, text=line, text_color="gray", font=("Segoe UI", 10), wraplength=230).pack()
        ctk.CTkLabel(p, text="Accuracy", text_color="gray").pack(pady=(6, 0))
        ctk.CTkSegmentedButton(p, values=ACCURACY, variable=self.accuracy,
                               command=lambda v: (cfg.update(accuracy=v), save_cfg())).pack(pady=(0, 2))
        ctk.CTkLabel(p, text="Deep: slower - re-reads every cell, retries doubtful images", text_color="gray",
                     font=("Segoe UI", 10), wraplength=230).pack()
        r = FlowFrame(p)
        r.pack(pady=(8, 2))
        r.add(ctk.CTkButton(r, text="🔍 Extract Text", width=112, command=self.ocr_current))
        r.add(ctk.CTkButton(r, text="✂ Select Area", width=112, command=self.select_area, **PURPLE))
        ctk.CTkButton(p, text="⚙ Settings", command=self.settings, **GRAY).pack(pady=(2, 10))

    def build_results(self, p):
        """Panel 3: one card per image + buttons that copy all results."""
        ctk.CTkLabel(p, text="📄 OCR RESULTS", font=("Segoe UI", 14, "bold")).pack(pady=(10, 2))
        self.results = ctk.CTkScrollableFrame(p)
        self.results.pack(fill="both", expand=True, padx=6, pady=4)
        f = FlowFrame(p)
        f.pack(fill="x", padx=4, pady=(2, 8))
        for txt, cmd in [("Copy Selected", self.copy_sel), ("Copy All", lambda: self.copy(self.combined_text())),
                         ("Copy Plain", lambda: self.copy(layout.to_plain(self.combined_text()))),
                         ("Copy Original OCR", lambda: self.copy(self.combined_text("raw"))),
                         ("🧩 Combine → Editor", lambda: self.sync_editor(True)), ("Clear", self.clear_all)]:
            f.add(ctk.CTkButton(f, text=txt, width=118, height=28, command=cmd))

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
            for f, _, _ in self.pane_sizes:
                self.panes.forget(f)
        else:
            for f, w, m in self.pane_sizes:
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

    def records(self):
        """Every item and every captured area (they all have a result text box)."""
        for it in self.items:
            yield it
            yield from it["areas"]

    def set_status(self, rec, status):
        """Change a record's status and update ONLY the labels that show it (no full redraw - fast)."""
        rec["status"] = status
        owner = rec.get("parent") or rec
        try:
            if rec.get("qinfo") is not None and rec in self.items:
                rec["qinfo"].configure(text=f"{self.items.index(rec) + 1}. {rec['name'][:13]}\n{ICON[status]}")
            if rec.get("slabel") is not None:
                rec["slabel"].configure(text=self.card_caption(owner, rec))
        except tk.TclError:
            pass

    # ================================================================ queue
    def new_item(self, img, name):
        th = img.copy()
        th.thumbnail((90, 60))
        return {"img": img, "name": name, "status": "waiting", "th": th, "sel": tk.BooleanVar(), "md": "", "raw": "",
                "res": None, "swap": False, "kind": "", "tb": None, "rendered": "", "areas": [], "area_count": 0,
                "parent": None, "card": None, "qinfo": None, "slabel": None}

    def add_image(self, img, name, at=None, show=True):
        """Add an image (at the end, or at index `at`). Returns the item, or None at the batch limit."""
        if len(self.items) >= cfg["batch_limit"]:
            messagebox.showwarning("Batch limit reached", f"Limit is {cfg['batch_limit']} images. Remove one, raise the "
                                   "limit in Settings, or capture areas INTO an existing image (they do not count).")
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
            it["qinfo"] = info
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
        img.thumbnail((max(120, self.pane_sizes[1][1] - 30), 340))
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
        """Open the Select Area tool for an image (default: the previewed one)."""
        if it is None:
            if self.current is None:
                return self.status("Select an image first")
            it = self.items[self.current]
        AreaSelector(self, it["img"], lambda crop, n, target: self.add_area(it, crop, n, target),
                     lambda img: self.replace_image(it, img))

    def add_area(self, src, crop, n=0, target="same"):
        """A box from the Select Area tool.

        target "same": OCR it and ADD the result to `src` (it stays Image N and uses no batch slot);
        target "new" : the box becomes a new image right after `src`.
        Returns False when it could not be added (batch limit).
        """
        if target == "new":
            at = self.items.index(src) + 1 if src in self.items else len(self.items)
            new = self.add_image(crop, f"{os.path.splitext(src['name'])[0]} · area {n}", at=at, show=False)
            if not new:
                return False
            self.run_ocr(new, self.mode.get())
            return True
        src["area_count"] += 1
        rec = self.new_item(crop, f"area {src['area_count']}")
        rec.update(parent=src, n=src["area_count"])
        src["areas"].append(rec)
        self.refresh_card(src)
        self.run_ocr(rec, self.mode.get())
        return True

    def replace_image(self, it, img):
        """The picture of an image was cropped / rotated in the Select Area tool."""
        it.setdefault("orig", it["img"])                       # the very first picture is kept
        it["img"] = img
        th = img.copy()
        th.thumbnail((90, 60))
        it["th"] = th
        it["status"] = "waiting"
        self.refresh_all()
        if self.current is not None and self.items[self.current] is it:
            self.show(self.current)
        self.status("Picture changed - press ⚡ Process All or ↻ on its card to read it again")

    # ================================================================ result cards (panel 3)
    def save_cards(self):
        """Copy text the user TYPED in a card back into its record (the record is the source of truth)."""
        for rec in self.records():
            if rec.get("tb") is not None:
                try:
                    cur = rec["tb"].get("1.0", "end-1c")
                except tk.TclError:
                    continue
                if cur != rec["rendered"]:               # only if the USER typed: programmatic changes to rec["md"] must survive
                    rec["md"] = rec["rendered"] = cur

    def card_caption(self, owner, rec):
        """Small grey text beside 'Image N' / 'Area n': file name, status."""
        if rec is owner:
            return f"{rec['name'][:30]}\n{ICON[rec['status']]}"
        return ICON[rec["status"]]

    def refresh_results(self):
        """Redraw one card per image: 'Image N', thumbnail, buttons, editable text, break line."""
        self.save_cards()
        for w in self.results.winfo_children():
            w.destroy()
        self.active = None
        for it in self.items:
            it["card"] = ctk.CTkFrame(self.results, fg_color="transparent")
            it["card"].pack(fill="x")
            self.build_card(it)
            ctk.CTkFrame(self.results, height=3, fg_color="gray40").pack(fill="x", pady=10)     # break line between images

    def refresh_card(self, it):
        """Redraw ONE card (after its OCR finished) - much faster than redrawing all of them."""
        if it in self.items and it.get("card") is not None:
            self.save_cards()
            self.build_card(it)

    def build_card(self, it):
        """Fill it["card"]: header, buttons, the text of the image and the text of every captured area."""
        card = it["card"]
        for w in card.winfo_children():
            w.destroy()
        i = self.items.index(it)
        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text="", image=ctk.CTkImage(it["th"], size=it["th"].size)).pack(side="left")
        ctk.CTkLabel(head, text=f"Image {i + 1}", font=("Segoe UI", 20, "bold")).pack(side="left", padx=10)
        it["slabel"] = ctk.CTkLabel(head, text=self.card_caption(it, it), text_color="gray", justify="left", anchor="w")
        it["slabel"].pack(side="left")
        row = FlowFrame(card)
        row.pack(fill="x")
        for txt, cmd in [("Copy", lambda: self.copy_item(it)), ("↻ Smart", lambda: self.run_ocr(it, "Smart")),
                         ("↻ Raw", lambda: self.run_ocr(it, "Raw")), ("↻ AI", lambda: self.run_ocr(it, "AI Smart")),
                         ("⇄ Swap", lambda: self.swap(it)), ("✂ Area", lambda: self.select_area(it)),
                         ("🗑", lambda: self.remove_items([it]))]:
            row.add(ctk.CTkButton(row, text=txt, width=50, height=26, command=cmd, **GRAY))
        self.card_box(card, it, 170)
        for a in it["areas"]:                                   # captured areas of this image
            ah = FlowFrame(card)
            ah.pack(fill="x", pady=(6, 0))
            ah.add(ctk.CTkLabel(ah, text=f"✂ Area {a['n']}", font=("Segoe UI", 13, "bold")))
            a["slabel"] = ah.add(ctk.CTkLabel(ah, text=self.card_caption(it, a), text_color="gray"))
            for txt, cmd in [("Copy", lambda a=a: self.copy_item(a)), ("⇄", lambda a=a: self.swap(a)),
                             ("🗑", lambda a=a: self.remove_area(a))]:
                ah.add(ctk.CTkButton(ah, text=txt, width=36, height=24, command=cmd, **GRAY))
            self.card_box(card, a, 100)

    def card_box(self, card, rec, height):
        """The editable text box of a record."""
        tb = ctk.CTkTextbox(card, height=height, undo=True, font=("Consolas", 13), wrap="none")
        tb.pack(fill="x", pady=4)
        tb.insert("1.0", rec["md"])
        rec["rendered"] = rec["md"]
        tb.bind("<FocusIn>", lambda e, t=tb: setattr(self, "active", t))
        rec["tb"] = tb

    def remove_area(self, a):
        parent = a["parent"]
        self.save_cards()
        parent["areas"].remove(a)
        self.refresh_card(parent)
        self.sync_editor()

    def item_text(self, it, field="md"):
        """Text of an image followed by the text of its captured areas."""
        parts = [(it[field] or "").strip()] + [f"#### Area {a['n']}\n{(a[field] or '').strip()}"
                                                for a in it["areas"] if (a[field] or "").strip()]
        return "\n\n".join(p for p in parts if p)

    def copy_item(self, rec):
        self.save_cards()
        self.copy(self.item_text(rec) if not rec.get("parent") else rec["md"])

    def swap(self, rec):
        """Swap the two table columns of one image (or one captured area)."""
        self.save_cards()
        if rec["res"] is None or rec["res"].kind != "bilingual":
            return self.status("Swap works on bilingual tables from Smart OCR")
        rec["swap"] = not rec["swap"]
        rec["md"] = layout.to_markdown(rec["res"], cfg["lang"], cfg["native"], rec["swap"])
        self.refresh_card(rec.get("parent") or rec)
        self.sync_editor()

    def combined_text(self, field="md"):
        """All images in order: '## Image N', file name, text (+ areas) - separated by a horizontal line."""
        self.save_cards()
        parts = [f"## Image {i}\n*{it['name']}*\n\n{self.item_text(it, field)}"
                 for i, it in enumerate(self.items, 1) if self.item_text(it, field)]
        return "\n\n---\n\n".join(parts)

    def clear_all(self):
        if self.items and messagebox.askyesno("Clear", "Clear the OCR text of ALL images? (the images stay in the queue)"):
            for it in self.items:
                it.update(md="", raw="", res=None, swap=False, kind="", status="waiting", areas=[], area_count=0)
            self.refresh_all()
            self.sync_editor()

    # ================================================================ OCR (three modes, three accuracy levels)
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

    def smart(self, img, min_pairs):
        """Smart OCR with the chosen accuracy. Returns the best layout.Result.

        Fast     - first pass only (no grid completion)
        Balanced - first pass + every grid cell re-read (finds missing and cut-off cells)
        Deep     - Balanced + single-language voting; if cells are still doubtful or unreadable the image is
                   read again at a larger scale and the more complete result wins
        """
        code, c1, c2 = self.codes()
        level = cfg["accuracy"]                              # plain value: Tk variables must not be read from a worker thread
        best = None
        for scale in ((None, 3) if level == "Deep" else (None,)):
            words, g = ocr_engine.read_words(img, code, scale)
            reader = None if level == "Fast" else ocr_engine.make_cell_reader(g, code, c1, c2)
            res = layout.analyze(words, cfg["lang"], cfg["min_conf"], ocr_engine.make_refiner(g, c1, c2), reader,
                                 min_pairs=min_pairs, size=g.size, deep=(level == "Deep"))
            if best is None or layout.score(res) > layout.score(best):
                best = res
            if res.kind != "bilingual" or (not res.unread and not res.low):
                break
        return best

    def read(self, rec, mode):
        """Worker thread: run OCR in `mode`. Returns (mode, output, warning, note)."""
        if mode == "Raw":
            return "Raw", ocr_engine.read_raw(rec["img"], self.codes()[0]), None, ""
        res = self.smart(rec["img"], 1 if rec.get("parent") else 3)
        if mode == "Smart":
            return "Smart", res, None, ""
        hint = (layout.to_markdown(res, cfg["lang"], cfg["native"]) if res.kind == "bilingual" else res.raw)
        try:
            text = self.ai_smart(rec["img"], hint + "\n\nAll OCR lines:\n" + res.raw)
        except Exception as e:                                # no AI available -> still give the Smart result
            return "Smart", res, str(e) or e.__class__.__name__, ""
        extra = [(res.title, res.subtitle)] if cfg["title_vocab"] and res.title and res.subtitle else []
        text, added = layout.merge_missing(text, res.rows, extra)          # the AI can never make OCR words vanish
        return "AI Smart", text, None, (f" (+{added} item(s) the AI left out were added from the OCR)" if added else "")

    def apply(self, rec, mode, out, warn=None, note=""):
        """Store an OCR result in its record; returns a one-line summary for the status bar."""
        if mode == "Raw":
            rec.update(kind="raw", raw=out, res=None, swap=False, md=re.sub(r"\n{3,}", "\n\n", out).strip())
            info = "Raw text (complete)"
        elif mode == "Smart":
            rec.update(kind="smart", res=out, raw=out.raw, swap=False, md=layout.to_markdown(out, cfg["lang"], cfg["native"]))
            info = layout.status_line(out, cfg["lang"], cfg["native"])
            if warn:
                info = f"⚠ AI Smart unavailable ({warn[:80]}) – showing the Smart result. " + info
        else:
            rec.update(kind="ai", res=None, swap=False, md=out.strip())
            info = "AI Smart notes – please double-check them" + note
        rec["status"] = "done"
        return info

    def run_ocr(self, rec, mode):
        """OCR one image (or captured area) in the given mode, then update its card and the editor."""
        self.save_cards()
        owner = rec.get("parent") or rec
        self.set_status(rec, "working")
        if mode == "AI Smart":
            self.status("🤖 AI Smart is reading the picture… (local AI can take a minute)")

        def done(r):
            info = self.apply(rec, *r)
            self.refresh_card(owner)
            self.set_status(rec, "done")
            self.sync_editor()
            self.status(info if info.startswith("⚠") else "✓ " + info)

        self.bg(lambda: self.read(rec, mode), done, lambda msg: self.set_status(rec, "error"))

    def ocr_current(self):
        if self.current is None:
            return self.status("Select an image first")
        self.run_ocr(self.items[self.current], self.mode.get())

    def process_all(self):
        """OCR every unfinished image one after another (a queue), in the chosen mode, with a progress bar."""
        todo = [it for it in self.items if it["status"] != "done"]
        mode = self.mode.get()
        if not todo:
            return self.status("Nothing to process")
        self.save_cards()
        self.progress.set(0)
        self.progress.pack(side="left", padx=12)

        def run():
            for n, it in enumerate(todo, 1):
                self.post(lambda it=it, n=n: (self.set_status(it, "working"), self.progress.set((n - 1) / len(todo)),
                                              self.status(f"Processing image {n} / {len(todo)} ({mode}, {self.accuracy.get()})…")))
                try:
                    r, ok = self.read(it, mode), True
                except Exception:
                    r, ok = None, False                       # mark this image as error, go on with the rest
                self.post(lambda it=it, r=r, ok=ok: self.apply(it, *r) if ok else self.set_status(it, "error"))
            self.post(lambda: (self.progress.pack_forget(), self.refresh_all(), self.sync_editor(),
                               self.status(f"✓ Finished {len(todo)} image(s)")))
        threading.Thread(target=run, daemon=True).start()

    # ================================================================ editor sync + AI buttons
    def notes_md(self, rec, vocab_heading=True):
        """Study-notes Markdown of one record for the editor (headings + bullets by default)."""
        md = (rec["md"] or "").strip()
        if not md:
            return ""
        if rec["kind"] == "ai":
            return md
        if rec["kind"] == "smart":
            return layout.to_notes(rec["res"], md, cfg["title_vocab"], vocab_heading)
        if rec["kind"] == "raw":
            return layout.text_notes(md, "Raw text") if vocab_heading else "\n".join(x.strip() for x in md.splitlines() if x.strip())
        return md

    def editor_blocks(self):
        """Whole editor document: for each image 'Image N' (title), file name, notes, its areas, separator line."""
        self.save_cards()
        out = []
        for i, it in enumerate(self.items, 1):
            notes = self.notes_md(it)
            areas = [(a, self.notes_md(a, False)) for a in it["areas"]]
            areas = [(a, t) for a, t in areas if t]
            if not notes and not areas:
                continue
            out += [rt.Block("title", runs=[rt.Run(f"Image {i}")]),
                    rt.Block(runs=[rt.Run(it["name"], italic=True, size=10, color="#888888")])]
            if notes:
                out += rt.md_to_blocks(notes, top="h1")
            for a, t in areas:                                   # captured areas stay under THEIR image
                out.append(rt.Block("h3", runs=[rt.Run(f"Area {a['n']}")]))
                out += rt.md_to_blocks(t, top="h3")
            out.append(rt.Block(hr=True))
        return out

    def sync_editor(self, force=False):
        """Rebuild the editor from the OCR results.

        Automatic updates never overwrite text the user edited (editor.dirty); the user can still force it
        with '⟳ Update from OCR' / 'Combine → Editor' (and undo it with '⤺ Restore').
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
        w.geometry("440x740")
        w.grab_set()
        v = {}

        def row(label, key, values=None, combo=False):
            ctk.CTkLabel(w, text=label).pack(anchor="w", padx=20, pady=(8, 0))
            v[key] = tk.StringVar(value=("Yes" if cfg[key] else "No") if isinstance(cfg[key], bool) else str(cfg[key]))
            if combo:
                box = ctk.CTkComboBox(w, variable=v[key], values=values or [])
            else:
                box = ctk.CTkOptionMenu(w, variable=v[key], values=values) if values else ctk.CTkEntry(w, textvariable=v[key])
            box.pack(fill="x", padx=20)
            return box
        row("Learning language (OCR + first table column)", "lang", list(LANGS))
        row("Your language (second column / AI answers)", "native", ["English", "Urdu", "Turkish", "Arabic", "Persian"])
        row("Level", "level", ["Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced"])
        row("Image batch limit", "batch_limit", ["5", "10", "20", "30", "50", "100"])
        row("OCR accuracy (Deep = slower, most complete)", "accuracy", ACCURACY)
        row("Ignore OCR text below this confidence (0-100)", "min_conf", ["30", "40", "45", "55", "65", "75"])
        row("Also list the picture's title as a vocabulary item", "title_vocab", ["Yes", "No"])
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
                cfg[k] = (int(var.get()) if k in ("batch_limit", "min_conf") else var.get() == "Yes" if k == "title_vocab"
                          else var.get().strip())
            save_cfg()
            self.accuracy.set(cfg["accuracy"])
            ctk.set_appearance_mode(cfg["theme"])
            self.refresh_all()
            self.check_ai()
            w.destroy()
        ctk.CTkButton(w, text="Save Settings", command=save).pack(pady=14)
