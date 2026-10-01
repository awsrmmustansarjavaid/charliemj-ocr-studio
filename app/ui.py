"""
ui.py - the CustomTkinter window of Charlie MJ OCR & Language Studio.

Window layout
-------------
    +-----------------+-----------------+---------------------------------------+
    | INPUT / QUEUE   | PREVIEW         | Formatting toolbar                    |
    | add, screenshot | selected image  | Local-AI toolbar                      |
    | paste, folder   | Smart | Raw     | [Results] [Combined] tabs             |
    | image cards 1-N | Extract / AI OCR|   Image 1 ... table ... ----------    |
    | remove / undo   | Settings        |   Image 2 ... table ... ----------    |
    | Process All     |                 | Copy / Export buttons                 |
    +-----------------+-----------------+---------------------------------------+

Key ideas
---------
* Every queue image owns ONE result card, titled "Image N" (N = its position in the
  queue). Delete or reorder images and the numbers update automatically.
* Each card is an independent, editable text box - results are never merged into one
  big block. "Combine All OCR" builds a joined document (with "---" separators) on demand.
* The `items` list is the single source of truth. Cards are rebuilt from it, and
  card text is saved back into it before every rebuild/export (see save_cards()).
* Slow work (OCR, local AI) runs in background threads (bg()) so the window never freezes.
  Threads never touch widgets: they hand results to the UI thread through a queue (post()/poll()).
"""
import csv
import os
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageGrab, ImageTk

from . import layout, local_ai, ocr_engine
from .config import EXTS, ICON, LANGS, cfg, save_cfg

# --------------------------------------------------------------------------- AI prompts
# Vocabulary shape that extract_pairs() can read back for the CSV export.
FMT = "Vocabulary lines must look exactly like: - **word** — meaning. "
NOINVENT = "Never invent or guess words that are not in the text; keep unclear words unchanged. "


def ctx():
    """One-sentence learner profile put at the start of every AI prompt."""
    return f"The learner is studying {cfg['lang']}, native language {cfg['native']}, level {cfg['level']}. "


# Button label -> (prompt builder, "append" below the text | "replace" the selection)
ACTIONS = {
    "✨ Learn This": (lambda t: ctx() + NOINVENT + "Turn this text into learning notes in Markdown: ### title, "
                      "## Translation, ## Vocabulary (useful words for this level, base forms), ## Grammar note. "
                      + FMT + "Return only Markdown.\n\n" + t, "append"),
    "Clean": (lambda t: ctx() + NOINVENT + "Fix OCR mistakes, keep the original language, organise as Markdown with "
              "headings and bullets. " + FMT + "Return only Markdown.\n\n" + t, "replace"),
    "Translate": (lambda t: f"Translate to {cfg['native']}. Return only the translation.\n\n" + t, "append"),
    "Explain": (lambda t: ctx() + "Explain this word/sentence: meaning, pronunciation, base form, part of speech, "
                "2 example sentences with translations. Short Markdown.\n\n" + t, "append"),
    "Vocabulary": (lambda t: ctx() + NOINVENT + "Extract the most useful vocabulary as bullets. " + FMT
                   + "Only bullets.\n\n" + t, "append"),
    "Flashcards": (lambda t: ctx() + NOINVENT + "Make flashcards. " + FMT + "Front = " + cfg["lang"]
                   + ", back = meaning. Only bullets.\n\n" + t, "append"),
    "📊 Table": (lambda t: ctx() + NOINVENT + f"Organise this OCR text into ONE Markdown table with columns "
                 f"'#', '{cfg['lang']}', '{cfg['native']}' (number the rows). Keep the original words exactly. "
                 "Return only the table.\n\n" + t, "replace"),
}


class App(ctk.CTk):
    """Main window."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(cfg["theme"])
        ctk.set_default_color_theme("blue")
        self.title("Charlie MJ OCR & Language Studio")
        self.geometry("1400x800")
        self.minsize(1100, 640)

        # ---- runtime state (memory only) ----
        # item = {img, name, status, th, sel, md, raw, res, swap, tb}
        self.items = []        # the queue, in display order
        self.removed = []      # [(index, item)] removed last time, for Undo
        self.current = None    # index of the previewed image
        self.active = None     # text box that formatting / AI buttons act on
        self.mode = tk.StringVar(value=cfg["mode"])   # "Smart" or "Raw"
        self.q = queue.Queue()  # worker threads -> UI thread (callables to run)
        # 1x1 transparent image: CTkLabel.configure(image=None) is unreliable
        self.blank = ctk.CTkImage(Image.new("RGBA", (1, 1)), size=(1, 1))

        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_queue()
        self.build_preview()
        self.build_right()
        self.build_statusbar()
        # Ctrl+V pastes an image into the queue (but not while typing in a text box)
        self.bind("<Control-v>", lambda e: None if isinstance(self.focus_get(), tk.Text) else self.paste())
        self.poll()
        self.check_ai()

    # ================================================================= UI construction
    def build_queue(self):
        """Left column: input buttons, batch counter, numbered image cards, remove/process."""
        p = ctk.CTkFrame(self, width=300)
        p.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        p.grid_propagate(False)
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
            ctk.CTkButton(r, text=txt, width=80, fg_color="#7a2e2e", hover_color="#a03a3a",
                          command=cmd).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(p, text="⚡ Process All", height=38, command=self.process_all).pack(fill="x", padx=10, pady=8)
        self.refresh_queue()

    def build_preview(self):
        """Middle column: large preview, OCR mode switch, per-image OCR buttons."""
        p = ctk.CTkFrame(self, width=340)
        p.grid(row=0, column=1, sticky="ns", padx=5, pady=10)
        p.grid_propagate(False)
        ctk.CTkLabel(p, text="🖼 PREVIEW", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        self.prev = ctk.CTkLabel(p, text="No image selected")
        self.prev.pack(expand=True, fill="both", padx=8)
        ctk.CTkLabel(p, text="OCR mode").pack()
        ctk.CTkSegmentedButton(p, values=["Smart", "Raw"], variable=self.mode).pack(pady=(0, 6))
        r = ctk.CTkFrame(p, fg_color="transparent")
        r.pack(pady=4)
        ctk.CTkButton(r, text="🔍 Extract Text", width=130, command=self.ocr_current).pack(side="left", padx=3)
        ctk.CTkButton(r, text="🤖 AI OCR", width=110, fg_color="#6b46c1", hover_color="#805ad5",
                      command=self.ai_ocr_current).pack(side="left", padx=3)
        ctk.CTkButton(p, text="⚙ Settings", fg_color="gray30", command=self.settings).pack(pady=(4, 10))

    def build_right(self):
        """Right column: formatting + AI toolbars, Results/Combined tabs, copy/export rows."""
        p = ctk.CTkFrame(self)
        p.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        fm = ctk.CTkFrame(p, fg_color="transparent")          # row 0: Markdown formatting
        fm.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 2))
        for txt, cmd in [("Title", lambda: self.prefix("### ")), ("H1", lambda: self.prefix("## ")),
                         ("H2", lambda: self.prefix("### ")), ("H3", lambda: self.prefix("#### ")),
                         ("• Bullet", lambda: self.prefix("- ")), ("1. List", lambda: self.prefix("1. ")),
                         ("B", lambda: self.wrap("**")), ("I", lambda: self.wrap("*")),
                         ("― Line", lambda: self.insert_line("\n---\n")),
                         ("↶", lambda: self.undo(False)), ("↷", lambda: self.undo(True))]:
            ctk.CTkButton(fm, text=txt, width=52, height=28, fg_color="gray30", command=cmd).pack(side="left", padx=2)

        fa = ctk.CTkFrame(p, fg_color="transparent")          # row 1: local AI buttons
        fa.grid(row=1, column=0, sticky="ew", padx=6, pady=2)
        for name in ACTIONS:
            ctk.CTkButton(fa, text=name, width=84, height=28, fg_color="#6b46c1", hover_color="#805ad5",
                          command=lambda n=name: self.ai_action(n)).pack(side="left", padx=2)

        self.tabs = ctk.CTkTabview(p)                          # row 2: results / combined
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)
        self.tabs.add("Results")
        self.tabs.add("Combined")
        self.res_frame = ctk.CTkScrollableFrame(self.tabs.tab("Results"))
        self.res_frame.pack(fill="both", expand=True)
        self.combined = ctk.CTkTextbox(self.tabs.tab("Combined"), undo=True, font=("Consolas", 13), wrap="none")
        self.combined.pack(fill="both", expand=True)
        self.combined.bind("<FocusIn>", lambda e: self.set_active(self.combined))

        r1 = ctk.CTkFrame(p, fg_color="transparent")           # row 3: copy buttons
        r1.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 0))
        for txt, cmd in [("Copy Selected", self.copy_sel), ("Copy All", lambda: self.copy(self.combined_text())),
                         ("Copy Plain", lambda: self.copy(self.plain(self.combined_text()))),
                         ("Copy Original OCR", lambda: self.copy(self.combined_raw())),
                         ("🧩 Combine All OCR", self.combine_all)]:
            ctk.CTkButton(r1, text=txt, width=110, height=28, command=cmd).pack(side="left", padx=2)
        r2 = ctk.CTkFrame(p, fg_color="transparent")           # row 4: save / export
        r2.grid(row=4, column=0, sticky="ew", padx=6, pady=(2, 8))
        for txt, cmd in [("Save (.md)", lambda: self.export("md")), ("Export TXT", lambda: self.export("txt")),
                         ("Export CSV", lambda: self.export("csv")), ("Clear box", self.clear_active)]:
            ctk.CTkButton(r2, text=txt, width=110, height=28, command=cmd).pack(side="left", padx=2)
        self.refresh_results()

    def build_statusbar(self):
        """Bottom bar: message on the left, local-AI state on the right."""
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=4)
        self.statusbar = ctk.CTkLabel(bar, text="✓ Ready", anchor="w")
        self.statusbar.pack(side="left")
        self.ai_label = ctk.CTkLabel(bar, text="OCR: Local   |   AI: checking…", anchor="e")
        self.ai_label.pack(side="right")

    # ================================================================= helpers
    def status(self, t):
        """Show a message in the status bar."""
        self.statusbar.configure(text=t)

    def post(self, fn):
        """Thread-safe: ask the UI thread to run fn() soon (the only way threads touch the UI)."""
        self.q.put(fn)

    def poll(self):
        """UI thread: run everything the worker threads queued, then check again in 50 ms."""
        try:
            while True:
                try:
                    self.q.get_nowait()()
                except queue.Empty:
                    break
                except Exception as e:                    # a bad callback must not stop the loop
                    self.status(f"⚠ {str(e)[:200]}")
        finally:
            self.after(50, self.poll)

    def bg(self, fn, done):
        """Run fn() in a thread; call done(result) on the UI thread. Errors go to the status bar."""
        def work():
            try:
                res = fn()
            except Exception as e:
                msg = str(e)
                self.post(lambda: self.status(f"⚠ {msg[:200]}"))
            else:
                self.post(lambda: done(res))
        threading.Thread(target=work, daemon=True).start()

    def check_ai(self):
        """Background check: is the local Ollama server reachable? Updates the status bar."""
        def done(r):
            ok, models, _ = r
            self.ai_label.configure(text="OCR: Local   |   AI: " + (f"Ollama ✓ ({len(models)} models)" if ok else "not running (optional)"))
        self.bg(lambda: local_ai.status(cfg["ollama_url"]), done)

    def copy(self, t):
        """Put text on the clipboard."""
        if not t.strip():
            return self.status("Nothing to copy yet")
        self.clipboard_clear()
        self.clipboard_append(t)
        self.status("✓ Copied to clipboard")

    @staticmethod
    def plain(t):
        """Markdown -> plain text: drop #, **, *, table pipes and rule lines."""
        t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
        t = re.sub(r"^\s*\|[-| ]+\|\s*$", "", t, flags=re.M)           # table separator row
        t = re.sub(r"^\s*\|\s*\d*\s*\|\s*", "", t, flags=re.M)        # leading "| 3 |"
        t = t.replace("|", "\t").replace("*", "")
        return re.sub(r"^\s*-\s+", "• ", re.sub(r"\n{3,}", "\n\n", t), flags=re.M).strip()

    # ----------------------------------------------------------------- text-box helpers
    def set_active(self, tb):
        """Remember which text box the toolbars should act on."""
        self.active = tb

    def cur(self):
        """The active text box, or None (with a hint) if there is none."""
        try:
            if self.active is not None and self.active.winfo_exists():
                return self.active
        except tk.TclError:
            pass
        self.status("Click inside a result box first")
        return None

    def copy_sel(self):
        """Copy the highlighted text of the active box."""
        tb = self.cur()
        if tb:
            try:
                self.copy(tb.get("sel.first", "sel.last"))
            except tk.TclError:
                self.status("Select some text first")

    def clear_active(self):
        """Empty the active box."""
        tb = self.cur()
        if tb:
            tb.delete("1.0", "end")

    def undo(self, redo):
        """Undo / redo in the active box."""
        tb = self.cur()
        if tb:
            try:
                (tb.edit_redo if redo else tb.edit_undo)()
            except tk.TclError:
                pass

    def insert_line(self, s):
        """Insert text at the cursor of the active box."""
        tb = self.cur()
        if tb:
            tb.insert("insert", s)

    def prefix(self, pre):
        """Set the current line's Markdown prefix (heading/bullet/number), replacing any old one."""
        tb = self.cur()
        if not tb:
            return
        s, e = tb.index("insert linestart"), tb.index("insert lineend")
        t = re.sub(r"^(#{1,6}\s+|[-*]\s+|\d+\.\s+)", "", tb.get(s, e))
        tb.delete(s, e)
        tb.insert(s, pre + t)

    def wrap(self, m):
        """Wrap the selection with a Markdown marker (** bold, * italic)."""
        tb = self.cur()
        if not tb:
            return
        try:
            a, b = tb.index("sel.first"), tb.index("sel.last")
        except tk.TclError:
            return self.status("Select some text first")
        t = tb.get(a, b)
        tb.delete(a, b)
        tb.insert(a, m + t + m)

    # ================================================================= queue
    def add_image(self, img, name):
        """Add a PIL image to the queue. Returns False (and warns) at the batch limit."""
        if len(self.items) >= cfg["batch_limit"]:
            messagebox.showwarning("Batch limit reached",
                                   f"Limit is {cfg['batch_limit']}. Remove an image or change it in Settings.")
            return False
        th = img.copy()
        th.thumbnail((90, 60))
        self.items.append({"img": img, "name": name, "status": "waiting", "th": th, "sel": tk.BooleanVar(),
                           "md": "", "raw": "", "res": None, "swap": False, "tb": None})
        self.refresh_queue()
        self.refresh_results()
        self.show(len(self.items) - 1)
        return True

    def refresh_queue(self):
        """Rebuild the numbered image cards and the 'Batch: n / limit' counter."""
        for w in self.list.winfo_children():
            w.destroy()
        for i, it in enumerate(self.items):
            f = ctk.CTkFrame(self.list)
            f.pack(fill="x", pady=3)
            ctk.CTkCheckBox(f, text="", width=24, variable=it["sel"]).pack(side="left", padx=4)
            lb = ctk.CTkLabel(f, text="", image=ctk.CTkImage(it["th"], size=it["th"].size))
            lb.pack(side="left")
            info = ctk.CTkLabel(f, text=f"{i + 1}. {it['name'][:15]}\n{ICON[it['status']]}", justify="left", anchor="w")
            info.pack(side="left", padx=6)
            mv = ctk.CTkFrame(f, fg_color="transparent")          # ▲ ▼ reorder buttons
            mv.pack(side="right", padx=2)
            ctk.CTkButton(mv, text="▲", width=24, height=22, fg_color="gray30", command=lambda i=i: self.move(i, -1)).pack()
            ctk.CTkButton(mv, text="▼", width=24, height=22, fg_color="gray30", command=lambda i=i: self.move(i, 1)).pack(pady=(2, 0))
            for w in (f, lb, info):
                w.bind("<Button-1>", lambda e, i=i: self.show(i))
        self.count.configure(text=f"Batch: {len(self.items)} / {cfg['batch_limit']}")

    def show(self, i):
        """Display queue item i in the preview."""
        self.current = i
        img = self.items[i]["img"].copy()
        img.thumbnail((320, 520))
        self.prev.configure(image=ctk.CTkImage(img, size=img.size), text="")

    def clear_preview(self):
        """Reset the preview to its empty state."""
        self.current = None
        self.prev.configure(image=self.blank, text="No image selected")

    def move(self, i, d):
        """Move image i up (-1) or down (+1). Numbering ("Image N") follows automatically."""
        j = i + d
        if 0 <= j < len(self.items):
            self.save_cards()
            self.items[i], self.items[j] = self.items[j], self.items[i]
            self.refresh_queue()
            self.refresh_results()
            self.show(j)

    def add_files(self):
        """Multi-select file dialog."""
        for f in filedialog.askopenfilenames(filetypes=[("Images", " ".join("*" + e for e in EXTS))]):
            if not self.open_path(f):
                break

    def add_folder(self):
        """Add every supported image in a folder (up to the batch limit)."""
        d = filedialog.askdirectory()
        for f in sorted(os.listdir(d)) if d else []:
            if f.lower().endswith(EXTS) and not self.open_path(os.path.join(d, f)):
                break

    def open_path(self, path):
        """Load one image file into the queue. False = stop (limit reached); bad files are skipped."""
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            self.status(f"⚠ Could not open {os.path.basename(path)}")
            return True
        return self.add_image(img, os.path.basename(path))

    def paste(self):
        """Add an image (or copied image files) from the clipboard."""
        c = ImageGrab.grabclipboard()
        if isinstance(c, Image.Image):
            self.add_image(c.convert("RGB"), "pasted.png")
        elif isinstance(c, list):
            for f in c:
                if f.lower().endswith(EXTS):
                    self.open_path(f)
        else:
            self.status("No image in clipboard")

    def remove_items(self, gone):
        """Remove items (remembered for Undo) and refresh everything."""
        self.save_cards()
        self.removed = [(self.items.index(it), it) for it in gone]
        self.items = [it for it in self.items if it not in gone]
        self.clear_preview()
        self.refresh_queue()
        self.refresh_results()

    def remove_sel(self):
        """Remove ticked images (or the previewed one if none are ticked)."""
        gone = [it for it in self.items if it["sel"].get()]
        if not gone and self.current is not None:
            gone = [self.items[self.current]]
        if gone:
            self.remove_items(gone)

    def remove_all(self):
        """Empty the queue after confirmation."""
        if self.items and messagebox.askyesno("Remove all", "Remove all images from the queue?"):
            self.remove_items(list(self.items))

    def undo_remove(self):
        """Restore the last removed images at their old positions."""
        for i, it in sorted(self.removed, key=lambda x: x[0]):
            if len(self.items) < cfg["batch_limit"]:
                self.items.insert(min(i, len(self.items)), it)
        self.removed = []
        self.refresh_queue()
        self.refresh_results()

    # ================================================================= screenshot
    def snip(self):
        """Hide this window, then let the user drag a rectangle on a frozen screenshot."""
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
        cv.image = photo                     # keep a reference so Tk keeps the picture
        st = {}

        def down(e):
            st["x"], st["y"] = e.x, e.y
            st["r"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2)

        def move(e):
            if "r" in st:
                cv.coords(st["r"], st["x"], st["y"], e.x, e.y)

        def up(e):
            k = shot.width / sw              # canvas -> real screenshot pixels
            x1, x2 = sorted((st.get("x", 0), e.x))
            y1, y2 = sorted((st.get("y", 0), e.y))
            top.destroy()
            self.deiconify()
            if x2 - x1 > 5 and y2 - y1 > 5:
                self.add_image(shot.crop((int(x1 * k), int(y1 * k), int(x2 * k), int(y2 * k))).convert("RGB"),
                               "screenshot.png")

        def cancel(e=None):
            top.destroy()
            self.deiconify()
        cv.bind("<ButtonPress-1>", down)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", up)
        top.bind("<Escape>", cancel)

    # ================================================================= results (cards)
    def save_cards(self):
        """Copy the text of every visible card back into its item (cards are only a view)."""
        for it in self.items:
            tb = it.get("tb")
            try:
                if tb is not None and tb.winfo_exists():
                    it["md"] = tb.get("1.0", "end-1c")
            except tk.TclError:
                pass

    def refresh_results(self):
        """Rebuild one card per image: 'Image N' title, filename, buttons, editable text, separator."""
        self.save_cards()
        for it in self.items:
            it["tb"] = None
        self.active = None if self.active is not self.combined else self.active
        for w in self.res_frame.winfo_children():
            w.destroy()
        if not self.items:
            ctk.CTkLabel(self.res_frame, text="Add images, then press ⚡ Process All.\n"
                         "Each image gets its own result here.", text_color="gray").pack(pady=40)
        for i, it in enumerate(self.items):
            card = ctk.CTkFrame(self.res_frame)
            card.pack(fill="x", padx=4, pady=(6, 0))
            head = ctk.CTkFrame(card, fg_color="transparent")
            head.pack(fill="x", padx=6, pady=6)
            ctk.CTkLabel(head, text="", image=ctk.CTkImage(it["th"], size=it["th"].size)).pack(side="left")
            t = ctk.CTkFrame(head, fg_color="transparent")
            t.pack(side="left", padx=8)
            ctk.CTkLabel(t, text=f"Image {i + 1}", font=("Segoe UI", 18, "bold")).pack(anchor="w")
            ctk.CTkLabel(t, text=f"{it['name']}  ·  {ICON[it['status']]}", text_color="gray").pack(anchor="w")
            b = ctk.CTkFrame(head, fg_color="transparent")
            b.pack(side="right")
            for txt, cmd in [("Copy", lambda it=it: self.copy_card(it)),
                             ("↻ Smart", lambda it=it: self.ocr_item(it, "Smart")),
                             ("↻ Raw", lambda it=it: self.ocr_item(it, "Raw")),
                             ("⇄ Swap", lambda it=it: self.swap(it)),
                             ("🗑", lambda it=it: self.remove_items([it]))]:
                ctk.CTkButton(b, text=txt, width=64 if len(txt) > 2 else 36, height=26, fg_color="gray30",
                              command=cmd).pack(side="left", padx=2)
            lines = it["md"].count("\n") + 1
            tb = ctk.CTkTextbox(card, height=min(420, max(90, lines * 21 + 14)), undo=True,
                                font=("Consolas", 13), wrap="none")
            tb.pack(fill="x", padx=6, pady=(0, 8))
            tb.insert("1.0", it["md"])
            tb.bind("<FocusIn>", lambda e, tb=tb: self.set_active(tb))
            it["tb"] = tb
            # horizontal break line between the results of different images
            ctk.CTkFrame(self.res_frame, height=3, fg_color="gray40").pack(fill="x", padx=4, pady=(8, 0))

    def copy_card(self, it):
        """Copy one image's result."""
        self.save_cards()
        self.copy(it["md"])

    def swap(self, it):
        """Swap the original / translation columns of a bilingual table."""
        res = it.get("res")
        if res is None or res.kind != "bilingual":
            return self.status("Swap works on bilingual tables (Smart mode)")
        it["swap"] = not it["swap"]
        it["md"] = layout.to_markdown(res, cfg["lang"], cfg["native"], it["swap"])
        it["tb"] = None                      # detach the stale card text box (see apply())
        self.refresh_results()

    def combined_text(self):
        """All results joined: '## Image N', filename, text, and a '---' line between images."""
        self.save_cards()
        parts = [f"## Image {i + 1}\n*{it['name']}*\n\n{it['md'].strip()}"
                 for i, it in enumerate(self.items) if it["md"].strip()]
        return "\n\n---\n\n".join(parts)

    def combined_raw(self):
        """The untouched OCR text of every image, labelled 'Image N'."""
        parts = [f"Image {i + 1}\n{it['raw'].strip()}" for i, it in enumerate(self.items) if it["raw"].strip()]
        return "\n\n" .join(parts)

    def combine_all(self):
        """Fill the Combined tab with the joined document and switch to it."""
        text = self.combined_text()
        self.combined.delete("1.0", "end")
        self.combined.insert("1.0", text)
        self.tabs.set("Combined")
        self.status("✓ Combined " + (f"{text.count('## Image ')} result(s)" if text else "— nothing to combine yet"))

    # ================================================================= OCR
    def run_ocr(self, it, mode):
        """(worker thread) OCR one image in 'Smart' or 'Raw' mode and return the result dict."""
        code = LANGS[cfg["lang"]]
        if mode == "Raw":
            txt = ocr_engine.read_text(it["img"], code)
            return {"md": txt or "(no text found)", "raw": txt, "res": None}
        words, prepped = ocr_engine.read_words(it["img"], code)
        refine = ocr_engine.make_refiner(prepped, code.split("+")[0], LANGS[cfg["native"]].split("+")[0])
        res = layout.analyze(words, cfg["lang"], cfg["min_conf"], refine)
        return {"md": layout.to_markdown(res, cfg["lang"], cfg["native"]), "raw": res.raw, "res": res}

    def apply(self, it, out):
        """(UI thread) store an OCR result in its item.

        it["tb"] = None detaches the old card text box, otherwise save_cards() would copy
        its STALE text over the fresh result. The card is rebuilt by refresh_results().
        """
        it.update(md=out["md"], raw=out["raw"], res=out["res"], swap=False, status="done", tb=None)

    def ocr_item(self, it, mode):
        """OCR one image (used by the card buttons and 'Extract Text')."""
        it["status"] = "working"
        self.refresh_queue()
        self.status(f"🔍 {mode} OCR…")

        def done(out):
            self.apply(it, out)
            self.refresh_queue()
            self.refresh_results()
            res = out["res"]
            self.status("✓ " + (layout.status_line(res, cfg["lang"], cfg["native"]) if res else "Raw OCR finished"))

        def fail_safe():
            try:
                return self.run_ocr(it, mode)
            except Exception:
                it["status"] = "error"
                self.post(self.refresh_queue)
                raise
        self.bg(fail_safe, done)

    def ocr_current(self):
        """'Extract Text' button: OCR the previewed image in the chosen mode."""
        if self.current is None:
            return self.status("Select an image first")
        self.ocr_item(self.items[self.current], self.mode.get())

    def process_all(self):
        """OCR every image that is not done yet, one after another, in one background thread."""
        todo = [it for it in self.items if it["status"] != "done"]
        if not todo:
            return self.status("Nothing to process")
        mode = self.mode.get()
        for it in todo:
            it["status"] = "waiting"
        self.refresh_queue()

        def run():
            for n, it in enumerate(todo, 1):
                self.post(lambda n=n: self.status(f"🔍 Processing {n} / {len(todo)}…"))
                try:
                    out = self.run_ocr(it, mode)
                    self.post(lambda it=it, out=out: (self.apply(it, out), self.refresh_queue()))
                except Exception:
                    it["status"] = "error"
                    self.post(self.refresh_queue)
            self.post(lambda: (self.refresh_results(), self.status(f"✓ Finished {len(todo)} image(s)")))
        threading.Thread(target=run, daemon=True).start()

    # ================================================================= local AI
    def ai_ocr_current(self):
        """'AI OCR': ask the local vision model to read the previewed image."""
        if self.current is None:
            return self.status("Select an image first")
        it = self.items[self.current]
        it["status"] = "working"
        self.refresh_queue()
        self.status("🤖 Local AI is reading the image (can take a minute)…")
        prompt = (f"Read all text in this image exactly as written. The learner studies {cfg['lang']}. "
                  f"If it is vocabulary ({cfg['lang']} words with {cfg['native']} translations) return ONE Markdown "
                  f"table with columns '#', '{cfg['lang']}', '{cfg['native']}'. Otherwise return clean text with line "
                  "breaks. Never add, translate or invent words that are not visible. Return only the result.")

        def done(txt):
            self.apply(it, {"md": txt, "raw": txt, "res": None})
            self.refresh_queue()
            self.refresh_results()
            self.status("✓ AI OCR finished")

        def work():
            try:
                return local_ai.generate(cfg["ollama_url"], cfg["model"], prompt, it["img"])
            except Exception:
                it["status"] = "error"
                self.post(self.refresh_queue)
                raise
        self.bg(work, done)

    def ai_action(self, name):
        """Run an ACTIONS entry on the selection (or the whole active box) with the local model."""
        tb = self.cur()
        if not tb:
            return
        build, mode = ACTIONS[name]
        try:
            a, b = tb.index("sel.first"), tb.index("sel.last")
            text = tb.get(a, b)
        except tk.TclError:
            a = b = None
            text = tb.get("1.0", "end").strip()
        if not text.strip():
            return self.status("Nothing to send to AI")
        self.status(f"🤖 {name}… (local AI can take a minute)")

        def done(res):
            try:
                if not tb.winfo_exists():
                    return
                if mode == "replace" and a:
                    tb.delete(a, b)
                    tb.insert(a, res)
                elif mode == "replace":
                    tb.delete("1.0", "end")
                    tb.insert("1.0", res)
                else:
                    tb.insert("end", "\n\n" + res + "\n")
                self.status(f"✓ {name} done")
            except tk.TclError:
                pass
        self.bg(lambda: local_ai.generate(cfg["ollama_url"], cfg["model"], build(text)), done)

    # ================================================================= export
    def export(self, kind):
        """Save everything as Markdown ('md'), plain text ('txt') or CSV ('csv')."""
        text = self.combined_text()
        if not text:
            return self.status("Nothing to export yet")
        path = filedialog.asksaveasfilename(defaultextension="." + kind, filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        # utf-8-sig adds a BOM so Excel shows Turkish / Urdu / Arabic letters correctly
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            if kind == "md":
                f.write(text)
            elif kind == "txt":
                f.write(self.plain(text))
            else:
                w = csv.writer(f)
                w.writerow(["Image", cfg["lang"], cfg["native"]])
                seen = set()
                for i, it in enumerate(self.items, 1):
                    for a, b in layout.extract_pairs(it["md"]):
                        if a.lower() not in seen:      # duplicate detection across all images
                            seen.add(a.lower())
                            w.writerow([i, a, b])
        self.status(f"✓ Saved {os.path.basename(path)}")

    # ================================================================= settings
    def settings(self):
        """Modal Settings window with a local-AI connection test."""
        w = ctk.CTkToplevel(self)
        w.title("Settings")
        w.geometry("440x680")
        w.grab_set()
        vars_ = {}

        def row(label, key, values=None):
            ctk.CTkLabel(w, text=label).pack(anchor="w", padx=20, pady=(8, 0))
            v = tk.StringVar(value=str(cfg[key]))
            vars_[key] = v
            if values:
                ctk.CTkOptionMenu(w, variable=v, values=values).pack(fill="x", padx=20)
            else:
                ctk.CTkEntry(w, textvariable=v).pack(fill="x", padx=20)
        row("Learning language (OCR + table header)", "lang", list(LANGS))
        row("Your language (translations)", "native", list(LANGS))
        row("Level", "level", ["Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced"])
        row("Default OCR mode", "mode", ["Smart", "Raw"])
        row("Minimum OCR confidence (0-100, higher = cleaner)", "min_conf")
        row("Image batch limit", "batch_limit", ["5", "10", "20", "50", "100"])
        row("Theme", "theme", ["dark", "light"])
        row("Local AI address (Ollama, localhost only)", "ollama_url")
        ctk.CTkLabel(w, text="Local AI model (must be installed in Ollama)").pack(anchor="w", padx=20, pady=(8, 0))
        vars_["model"] = tk.StringVar(value=cfg["model"])
        combo = ctk.CTkComboBox(w, variable=vars_["model"], values=[cfg["model"]])
        combo.pack(fill="x", padx=20)
        diag = ctk.CTkLabel(w, text="", wraplength=380, justify="left")
        diag.pack(padx=20, pady=6)

        def test():
            """Diagnostic: is Ollama running, which models are installed?"""
            diag.configure(text="Testing…")
            url = vars_["ollama_url"].get().strip()

            def done(r):
                ok, models, msg = r
                diag.configure(text=("✓ " if ok else "✕ ") + msg)
                if models:
                    combo.configure(values=models)
            self.bg(lambda: local_ai.status(url), done)
        ctk.CTkButton(w, text="🔌 Test local AI connection", fg_color="gray30", command=test).pack(pady=4)

        def save():
            for k, v in vars_.items():
                val = v.get().strip()
                cfg[k] = int(val) if k in ("batch_limit", "min_conf") and val.isdigit() else val
            save_cfg()
            ctk.set_appearance_mode(cfg["theme"])
            self.refresh_queue()
            self.check_ai()
            w.destroy()
        ctk.CTkButton(w, text="Save Settings", command=save).pack(pady=14)
