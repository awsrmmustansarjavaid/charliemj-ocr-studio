"""
Charlie MJ OCR & Language Studio  -  main.py
=============================================

A lightweight, portable Windows desktop app for language learners.

Pipeline:  Image / Screenshot -> local OCR -> editable notes -> optional AI -> Copy / Export

File layout (top to bottom):
    1. Imports & start-up setup        (DPI awareness, paths, Tesseract location)
    2. Configuration                   (config.json load/save, constants)
    3. Service functions               (ocr_image, gemini, ctx)
    4. AI prompt table                 (ACTIONS)
    5. App class                       (the whole UI and its behaviour)
    6. Entry point

Design rules:
    * OCR is always LOCAL and works offline (Tesseract).
    * AI (Google Gemini) is OPTIONAL and runs only when a button is clicked.
    * Slow work (OCR, network) runs in background threads so the UI never freezes.
    * Everything the user saves lives next to the .exe, so the app stays portable.

See docs/ARCHITECTURE.md for diagrams and a deeper explanation.
"""

# ------------------------------------------------------------------ 1. IMPORTS
import os, sys, io, re, csv, json, base64, ctypes, threading   # standard library
import tkinter as tk                                            # base GUI toolkit
from tkinter import filedialog, messagebox                      # native dialogs
import customtkinter as ctk                                     # modern themed widgets
import requests                                                 # HTTP calls to Gemini
import pytesseract                                              # Tesseract OCR wrapper
from PIL import Image, ImageGrab, ImageOps, ImageTk             # image handling

# Make Windows report true pixel sizes so screenshot coordinates match the screen
# on high-DPI displays. Harmless (and ignored) on other platforms.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# Folder that contains the .exe (when frozen by PyInstaller) or this script.
# Using it for config/Tesseract paths is what makes the app "portable".
BASE = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

# ------------------------------------------------------------ 2. CONFIGURATION
CFG_PATH = os.path.join(BASE, "config.json")  # user settings file (git-ignored: holds API key)

# Default settings, used for any key missing from config.json
DEFAULTS = {
    "batch_limit": 20,             # max images allowed in the queue
    "lang": "Turkish",             # language being learned (drives OCR + AI)
    "native": "English",           # language translations are written in
    "level": "Beginner",           # learner level, used to filter AI vocabulary
    "api_key": "",                 # Google Gemini API key (optional)
    "model": "gemini-2.5-flash",   # Gemini model name
    "theme": "dark",               # "dark" or "light"
}

# Friendly language name -> Tesseract language codes ("+eng" helps with mixed text)
LANGS = {"Turkish": "tur+eng", "Urdu": "urd+eng", "Arabic": "ara+eng",
         "Persian": "fas+eng", "English": "eng"}

# Status label shown on each queue card
ICON = {"waiting": "○ Waiting", "working": "◌ Working", "done": "✓ Done", "error": "⚠ Error"}

# File extensions accepted as images
EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")

# If a "tesseract" folder sits next to the app, use that bundled copy.
# TESSDATA_PREFIX tells Tesseract where the language (.traineddata) files are.
_t = os.path.join(BASE, "tesseract")
if os.path.exists(os.path.join(_t, "tesseract.exe")):
    pytesseract.pytesseract.tesseract_cmd = os.path.join(_t, "tesseract.exe")
    os.environ["TESSDATA_PREFIX"] = os.path.join(_t, "tessdata")


def load_cfg():
    """Read config.json and merge it over DEFAULTS. Falls back to DEFAULTS on any error."""
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            return {**DEFAULTS, **json.load(f)}
    except Exception:
        return dict(DEFAULTS)


cfg = load_cfg()  # module-level settings shared by the whole app


def save_cfg():
    """Write the current settings to config.json (next to the app)."""
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ------------------------------------------------------------ 3. SERVICE FUNCTIONS
def ocr_image(img):
    """Run local OCR on a PIL image and return the extracted text.

    Pre-processing improves accuracy on flashcards/screenshots:
      * convert to grayscale
      * auto-contrast
      * upscale 2x when the image is small (Tesseract likes larger text)
    """
    g = ImageOps.autocontrast(ImageOps.grayscale(img))
    if g.width < 1000:
        g = g.resize((g.width * 2, g.height * 2), Image.LANCZOS)
    return pytesseract.image_to_string(g, lang=LANGS[cfg["lang"]]).strip()


def gemini(prompt, image=None):
    """Send a prompt (and optionally an image) to Google Gemini and return its text reply.

    Raises RuntimeError if no API key is set; network/HTTP errors propagate
    to the caller (see App.bg, which shows them in the status bar).
    """
    if not cfg["api_key"]:
        raise RuntimeError("Add your Gemini API key in Settings first.")
    parts = [{"text": prompt}]
    if image is not None:
        # Images are sent inline as base64-encoded JPEG
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "JPEG", quality=90)
        parts.append({"inline_data": {"mime_type": "image/jpeg",
                                      "data": base64.b64encode(buf.getvalue()).decode()}})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{cfg['model']}:generateContent"
    r = requests.post(url, headers={"x-goog-api-key": cfg["api_key"]},
                      json={"contents": [{"parts": parts}]}, timeout=90)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def ctx():
    """Return a one-sentence learner profile prepended to AI prompts for better answers."""
    return f"The learner is studying {cfg['lang']}, native language {cfg['native']}, level {cfg['level']}. "


# ------------------------------------------------------------ 4. AI PROMPT TABLE
# Vocabulary format rule; the CSV exporter parses exactly this "- **word** — meaning" shape.
FMT = "Vocabulary lines must look exactly like: - **word** — meaning. "

# Button label -> (function that builds the prompt from text, how to place the result)
# "replace" swaps the selected text; "append" adds the result at the end of the notes.
ACTIONS = {
    "✨ Learn This": (lambda t: ctx() + "Turn this text into learning notes in Markdown: a # title, the cleaned original, "
                      "## Translation, ## Vocabulary (only useful words for this level, base forms), ## Grammar note. "
                      + FMT + "Return only Markdown.\n\n" + t, "append"),
    "Clean": (lambda t: ctx() + "Fix OCR mistakes, keep the original language, organise as Markdown with # title, "
              "## headings and - bullets. " + FMT + "Return only Markdown.\n\n" + t, "replace"),
    "Translate": (lambda t: f"Translate to {cfg['native']}. Return only the translation.\n\n" + t, "append"),
    "Explain": (lambda t: ctx() + "Explain this word/sentence: meaning, pronunciation, base form, part of speech, "
                "2 example sentences with translations. Short Markdown.\n\n" + t, "append"),
    "Vocabulary": (lambda t: ctx() + "Extract the most useful vocabulary as bullets. " + FMT + "Only bullets.\n\n" + t, "append"),
    "Flashcards": (lambda t: ctx() + "Make flashcards. " + FMT + "Front = target language, back = meaning. Only bullets.\n\n" + t, "append"),
}


# ------------------------------------------------------------ 5. APPLICATION
class App(ctk.CTk):
    """Main window. Three columns: image queue | preview | notes editor, plus a status bar."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode(cfg["theme"])
        ctk.set_default_color_theme("blue")
        self.title("Charlie MJ OCR & Language Studio")
        self.geometry("1280x760")
        self.minsize(1000, 600)

        # ---- runtime state (kept in memory only) ----
        self.items = []       # queue: dicts with img, name, status, text, th (thumbnail), sel (checkbox var)
        self.removed = []     # items removed last time, for Undo
        self.current = None   # index of the image shown in the preview
        self.raw = ""         # all raw OCR text collected (for "Copy Original OCR")
        # 1x1 transparent image: CTkLabel.configure(image=None) is unreliable, so use this instead
        self.blank = ctk.CTkImage(Image.new("RGBA", (1, 1)), size=(1, 1))

        # ---- layout: column 2 (notes) stretches with the window ----
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.build_queue()
        self.build_preview()
        self.build_notes()
        self.statusbar = ctk.CTkLabel(self, text="✓ Ready   |   OCR: Local   |   AI: Optional", anchor="w")
        self.statusbar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=4)

        # Ctrl+V pastes an image into the queue (but not while typing in the editor)
        self.bind("<Control-v>", lambda e: self.paste() if self.focus_get() is not self.ed._textbox else None)

    # ---------------------------------------------------------- UI construction
    def build_queue(self):
        """Left column: input buttons, batch counter, scrollable image list, remove/process buttons."""
        p = ctk.CTkFrame(self, width=300)
        p.grid(row=0, column=0, sticky="ns", padx=(10, 5), pady=10)
        p.grid_propagate(False)  # keep fixed width
        ctk.CTkLabel(p, text="📥 INPUT", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        for txt, cmd in [("＋ Add Images", self.add_files), ("📸 Screenshot", self.snip),
                         ("📋 Paste Image", self.paste), ("📂 Add Folder", self.add_folder)]:
            ctk.CTkButton(p, text=txt, command=cmd).pack(fill="x", padx=10, pady=2)
        self.count = ctk.CTkLabel(p, text="")          # "Batch: 7 / 20"
        self.count.pack(pady=(8, 0))
        self.list = ctk.CTkScrollableFrame(p)           # holds one card per image
        self.list.pack(fill="both", expand=True, padx=6, pady=6)
        r = ctk.CTkFrame(p, fg_color="transparent")
        r.pack(fill="x", padx=6)
        for txt, cmd in [("🗑 Selected", self.remove_sel), ("🗑 All", self.remove_all), ("↶ Undo", self.undo_remove)]:
            ctk.CTkButton(r, text=txt, width=80, fg_color="#7a2e2e", hover_color="#a03a3a",
                          command=cmd).pack(side="left", padx=2, expand=True)
        ctk.CTkButton(p, text="⚡ Process All", height=38, command=self.process_all).pack(fill="x", padx=10, pady=8)
        self.refresh()

    def build_preview(self):
        """Middle column: large preview of the selected image plus per-image OCR buttons."""
        p = ctk.CTkFrame(self, width=420)
        p.grid(row=0, column=1, sticky="ns", padx=5, pady=10)
        p.grid_propagate(False)
        ctk.CTkLabel(p, text="🖼 PREVIEW", font=("Segoe UI", 14, "bold")).pack(pady=(10, 4))
        self.prev = ctk.CTkLabel(p, text="No image selected")
        self.prev.pack(expand=True, fill="both", padx=8)
        r = ctk.CTkFrame(p, fg_color="transparent")
        r.pack(pady=6)
        ctk.CTkButton(r, text="🔍 Extract Text", command=self.ocr_current).pack(side="left", padx=3)
        ctk.CTkButton(r, text="🤖 AI OCR", fg_color="#6b46c1", hover_color="#805ad5",
                      command=self.ai_ocr_current).pack(side="left", padx=3)
        ctk.CTkButton(p, text="⚙ Settings", fg_color="gray30", command=self.settings).pack(pady=(0, 10))

    def build_notes(self):
        """Right column: formatting toolbar, AI toolbar, the editor, and copy/export buttons."""
        p = ctk.CTkFrame(self)
        p.grid(row=0, column=2, sticky="nsew", padx=(5, 10), pady=10)
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)  # the editor row stretches

        # Row 0 - Markdown formatting buttons
        fm = ctk.CTkFrame(p, fg_color="transparent")
        fm.grid(row=0, column=0, sticky="ew", padx=6, pady=(8, 2))
        for txt, cmd in [("Title", lambda: self.prefix("# ")), ("H1", lambda: self.prefix("## ")),
                         ("H2", lambda: self.prefix("### ")), ("H3", lambda: self.prefix("#### ")),
                         ("• Bullet", lambda: self.prefix("- ")), ("1. List", lambda: self.prefix("1. ")),
                         ("B", lambda: self.wrap("**")), ("I", lambda: self.wrap("*")),
                         ("― Line", lambda: self.ed.insert("insert", "\n---\n")),
                         ("↶", lambda: self.safe(self.ed.edit_undo)), ("↷", lambda: self.safe(self.ed.edit_redo))]:
            ctk.CTkButton(fm, text=txt, width=52, height=28, fg_color="gray30", command=cmd).pack(side="left", padx=2)

        # Row 1 - AI buttons, generated from the ACTIONS table
        fa = ctk.CTkFrame(p, fg_color="transparent")
        fa.grid(row=1, column=0, sticky="ew", padx=6, pady=2)
        for name in ACTIONS:
            ctk.CTkButton(fa, text=name, width=80, height=28, fg_color="#6b46c1", hover_color="#805ad5",
                          command=lambda n=name: self.ai_action(n)).pack(side="left", padx=2)

        # Row 2 - the notes editor (undo=True enables Ctrl+Z / Ctrl+Y history)
        self.ed = ctk.CTkTextbox(p, undo=True, font=("Segoe UI", 15), wrap="word")
        self.ed.grid(row=2, column=0, sticky="nsew", padx=6, pady=4)

        # Row 3 - copy and export buttons
        fc = ctk.CTkFrame(p, fg_color="transparent")
        fc.grid(row=3, column=0, sticky="ew", padx=6, pady=(2, 8))
        for txt, cmd in [("Copy Selected", self.copy_sel),
                         ("Copy All", lambda: self.copy(self.ed.get("1.0", "end").strip())),
                         ("Copy Plain", lambda: self.copy(self.plain(self.ed.get("1.0", "end")))),
                         ("Copy Original OCR", lambda: self.copy(self.raw)),
                         ("Clear", lambda: self.ed.delete("1.0", "end")),
                         ("Save", lambda: self.export("md")),
                         ("Export TXT", lambda: self.export("txt")),
                         ("Export CSV", lambda: self.export("csv"))]:
            ctk.CTkButton(fc, text=txt, width=90, height=28, command=cmd).pack(side="left", padx=2)

    # ---------------------------------------------------------- small helpers
    def status(self, t):
        """Show a message in the bottom status bar."""
        self.statusbar.configure(text=t)

    def safe(self, fn):
        """Call fn() and ignore Tk errors (e.g. undo when there is nothing to undo)."""
        try:
            fn()
        except tk.TclError:
            pass

    def bg(self, fn, done):
        """Run fn() in a background thread; call done(result) on the UI thread when finished.

        Errors are caught and shown in the status bar instead of crashing the app.
        self.after(0, ...) is how a worker thread safely talks to Tk.
        """
        def work():
            try:
                res = fn()
            except Exception as e:
                msg = str(e)
                self.after(0, lambda: self.status(f"⚠ {msg[:150]}"))
            else:
                self.after(0, lambda: done(res))
        threading.Thread(target=work, daemon=True).start()

    def copy(self, t):
        """Put text on the Windows clipboard."""
        self.clipboard_clear()
        self.clipboard_append(t)
        self.status("✓ Copied to clipboard")

    def copy_sel(self):
        """Copy only the text currently highlighted in the editor."""
        try:
            self.copy(self.ed.get("sel.first", "sel.last"))
        except tk.TclError:
            self.status("Select some text first")

    @staticmethod
    def plain(t):
        """Convert Markdown to plain text: drop #, **, * markers and turn '- ' into bullets."""
        t = re.sub(r"^#{1,6}\s+", "", t, flags=re.M)
        t = re.sub(r"\*+", "", t)
        return re.sub(r"^\s*-\s+", "• ", t, flags=re.M).strip()

    # ---------------------------------------------------------- editor formatting
    def prefix(self, pre):
        """Set the current line's Markdown prefix (heading/bullet/number), replacing any old one."""
        s, e = self.ed.index("insert linestart"), self.ed.index("insert lineend")
        t = re.sub(r"^(#{1,6}\s+|[-*]\s+|\d+\.\s+)", "", self.ed.get(s, e))
        self.ed.delete(s, e)
        self.ed.insert(s, pre + t)

    def wrap(self, m):
        """Wrap the selected text with a Markdown marker (** for bold, * for italic)."""
        try:
            a, b = self.ed.index("sel.first"), self.ed.index("sel.last")
        except tk.TclError:
            return  # nothing selected
        t = self.ed.get(a, b)
        self.ed.delete(a, b)
        self.ed.insert(a, m + t + m)

    # ---------------------------------------------------------- image queue
    def add_image(self, img, name):
        """Add a PIL image to the queue. Returns False (and warns) when the batch limit is reached."""
        if len(self.items) >= cfg["batch_limit"]:
            messagebox.showwarning("Batch limit reached",
                                   f"Limit is {cfg['batch_limit']}. Remove an image or change it in Settings.")
            return False
        th = img.copy()
        th.thumbnail((90, 60))  # small copy used for the queue card
        self.items.append({"img": img, "name": name, "status": "waiting",
                           "text": "", "th": th, "sel": tk.BooleanVar()})
        self.refresh()
        self.show(len(self.items) - 1)
        return True

    def refresh(self):
        """Rebuild all queue cards and the 'Batch: n / limit' counter."""
        for w in self.list.winfo_children():
            w.destroy()
        for i, it in enumerate(self.items):
            f = ctk.CTkFrame(self.list)
            f.pack(fill="x", pady=3)
            ctk.CTkCheckBox(f, text="", width=24, variable=it["sel"]).pack(side="left", padx=4)
            lb = ctk.CTkLabel(f, text="", image=ctk.CTkImage(it["th"], size=it["th"].size))
            lb.pack(side="left")
            info = ctk.CTkLabel(f, text=f"{it['name'][:16]}\n{ICON[it['status']]}", justify="left", anchor="w")
            info.pack(side="left", padx=6)
            for w in (f, lb, info):  # clicking anywhere on the card previews the image
                w.bind("<Button-1>", lambda e, i=i: self.show(i))
        self.count.configure(text=f"Batch: {len(self.items)} / {cfg['batch_limit']}")

    def show(self, i):
        """Display queue item i in the preview panel."""
        self.current = i
        img = self.items[i]["img"].copy()
        img.thumbnail((400, 520))
        self.prev.configure(image=ctk.CTkImage(img, size=img.size), text="")

    def clear_preview(self):
        """Reset the preview panel to its empty state."""
        self.current = None
        self.prev.configure(image=self.blank, text="No image selected")

    def add_files(self):
        """Open a multi-select file dialog and add the chosen images."""
        for f in filedialog.askopenfilenames(filetypes=[("Images", " ".join("*" + e for e in EXTS))]):
            if not self.add_image(Image.open(f).convert("RGB"), os.path.basename(f)):
                break  # limit reached

    def add_folder(self):
        """Add every supported image from a chosen folder (up to the batch limit)."""
        d = filedialog.askdirectory()
        for f in sorted(os.listdir(d)) if d else []:
            if f.lower().endswith(EXTS) and not self.add_image(Image.open(os.path.join(d, f)).convert("RGB"), f):
                break

    def paste(self):
        """Add an image (or copied image files) from the Windows clipboard."""
        c = ImageGrab.grabclipboard()
        if isinstance(c, Image.Image):            # a bitmap, e.g. from Win+Shift+S
            self.add_image(c.convert("RGB"), "pasted.png")
        elif isinstance(c, list):                  # files copied in Explorer
            for f in c:
                if f.lower().endswith(EXTS):
                    self.add_image(Image.open(f).convert("RGB"), os.path.basename(f))
        else:
            self.status("No image in clipboard")

    def remove_sel(self):
        """Remove ticked images (or the previewed one if none are ticked). Stored for Undo."""
        gone = [it for it in self.items if it["sel"].get()]
        if not gone and self.current is not None:
            gone = [self.items[self.current]]
        if gone:
            self.removed = gone
            self.items = [it for it in self.items if it not in gone]
            self.clear_preview()
            self.refresh()

    def remove_all(self):
        """Empty the queue after confirmation. Stored for Undo."""
        if self.items and messagebox.askyesno("Remove all", "Remove all images from the queue?"):
            self.removed, self.items = list(self.items), []
            self.clear_preview()
            self.refresh()

    def undo_remove(self):
        """Put back the images removed most recently (respecting the batch limit)."""
        for it in self.removed:
            if len(self.items) < cfg["batch_limit"]:
                self.items.append(it)
        self.removed = []
        self.refresh()

    # ---------------------------------------------------------- screenshot capture
    def snip(self):
        """Start a screenshot: hide this window first so it isn't captured."""
        self.withdraw()
        self.after(350, self._snip)  # short delay lets the window finish hiding

    def _snip(self):
        """Show a full-screen frozen screenshot; the user drags a rectangle to select the area."""
        shot = ImageGrab.grab()
        top = tk.Toplevel()
        top.attributes("-fullscreen", True)
        top.attributes("-topmost", True)
        sw, sh = top.winfo_screenwidth(), top.winfo_screenheight()
        photo = ImageTk.PhotoImage(shot.resize((sw, sh)))
        cv = tk.Canvas(top, cursor="cross", highlightthickness=0)
        cv.pack(fill="both", expand=True)
        cv.create_image(0, 0, image=photo, anchor="nw")
        cv.image = photo  # keep a reference so Tk doesn't garbage-collect the picture
        st = {}           # drag state: start x/y and the rectangle id

        def down(e):      # mouse pressed: remember the start point
            st["x"], st["y"] = e.x, e.y
            st["r"] = cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2)

        def move(e):      # mouse dragged: resize the rectangle
            if "r" in st:
                cv.coords(st["r"], st["x"], st["y"], e.x, e.y)

        def up(e):        # mouse released: crop the screenshot and add it to the queue
            k = shot.width / sw  # scale between canvas and real screenshot pixels
            x1, x2 = sorted((st.get("x", 0), e.x))
            y1, y2 = sorted((st.get("y", 0), e.y))
            top.destroy()
            self.deiconify()
            if x2 - x1 > 5 and y2 - y1 > 5:  # ignore accidental clicks
                self.add_image(shot.crop((int(x1 * k), int(y1 * k), int(x2 * k), int(y2 * k))).convert("RGB"),
                               "screenshot.png")

        def cancel(e=None):  # Esc: abort
            top.destroy()
            self.deiconify()
        cv.bind("<ButtonPress-1>", down)
        cv.bind("<B1-Motion>", move)
        cv.bind("<ButtonRelease-1>", up)
        top.bind("<Escape>", cancel)

    # ---------------------------------------------------------- OCR
    def set_status(self, it, s):
        """Update one queue item's status and redraw the queue."""
        it["status"] = s
        self.refresh()

    def append(self, title, text):
        """Add OCR text to the notes under a '## title' heading and remember the raw text."""
        self.ed.insert("end", f"\n## {title}\n\n{text}\n")
        self.raw += f"\n{text}\n"

    def ocr_current(self):
        """Run local OCR on the previewed image."""
        if self.current is None:
            return self.status("Select an image first")
        it = self.items[self.current]
        self.set_status(it, "working")

        def done(t):
            it["text"] = t
            self.set_status(it, "done")
            self.append(it["name"], t)
            self.status("✓ OCR finished")
        self.bg(lambda: ocr_image(it["img"]), done)

    def ai_ocr_current(self):
        """Run AI (Gemini vision) OCR on the previewed image - useful for difficult fonts/scripts."""
        if self.current is None:
            return self.status("Select an image first")
        it = self.items[self.current]
        self.set_status(it, "working")

        def done(t):
            it["text"] = t
            self.set_status(it, "done")
            self.append(it["name"], t)
            self.status("✓ AI OCR finished")
        self.bg(lambda: gemini(f"Extract all {cfg['lang']} text from this image exactly as written. "
                               "Return only the text.", it["img"]), done)

    def process_all(self):
        """OCR every not-yet-done image in the queue, one after another, in one background thread."""
        todo = [it for it in self.items if it["status"] != "done"]
        if not todo:
            return self.status("Nothing to process")

        def run():
            for it in todo:
                self.after(0, lambda it=it: self.set_status(it, "working"))
                try:
                    it["text"] = ocr_image(it["img"])
                    ok = True
                except Exception:
                    ok = False  # mark this image as error but continue with the rest
                self.after(0, lambda it=it, ok=ok: (self.set_status(it, "done" if ok else "error"),
                                                     ok and self.append(it["name"], it["text"])))
            self.after(0, lambda: self.status("✓ Batch finished"))
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------- AI actions
    def ai_action(self, name):
        """Run one ACTIONS entry on the selected text (or the whole notes if nothing is selected)."""
        build, mode = ACTIONS[name]
        try:
            a, b = self.ed.index("sel.first"), self.ed.index("sel.last")
            text = self.ed.get(a, b)
        except tk.TclError:          # no selection -> use everything
            a = b = None
            text = self.ed.get("1.0", "end").strip()
        if not text.strip():
            return self.status("Nothing to send to AI")
        self.status(f"🤖 {name}...")

        def done(res):
            if mode == "replace" and a:        # replace the selection
                self.ed.delete(a, b)
                self.ed.insert(a, res)
            elif mode == "replace":            # replace everything
                self.ed.delete("1.0", "end")
                self.ed.insert("1.0", res)
            else:                               # append below existing notes
                self.ed.insert("end", "\n\n" + res + "\n")
            self.status(f"✓ {name} done")
        self.bg(lambda: gemini(build(text)), done)

    # ---------------------------------------------------------- export
    def export(self, kind):
        """Save the notes as 'md' (Markdown), 'txt' (plain) or 'csv' (Front,Back flashcards)."""
        path = filedialog.asksaveasfilename(defaultextension="." + kind, filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        t = self.ed.get("1.0", "end").strip()
        # utf-8-sig adds a BOM so Excel opens Turkish/Urdu/Arabic characters correctly
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            if kind == "txt":
                f.write(self.plain(t))
            elif kind == "md":
                f.write(t)
            else:
                w = csv.writer(f)
                w.writerow(["Front", "Back"])
                seen = set()
                # Match bullets shaped like: - **word** — meaning
                for m in re.finditer(r"^\s*[-*]\s*\**(.+?)\**\s+[—–-]\s+(.+)$", t, flags=re.M):
                    k = m.group(1).strip().lower()
                    if k not in seen:  # duplicate detection: one row per word
                        seen.add(k)
                        w.writerow([m.group(1).strip(), m.group(2).strip()])
        self.status(f"✓ Saved {os.path.basename(path)}")

    # ---------------------------------------------------------- settings window
    def settings(self):
        """Modal Settings window: languages, level, batch limit, theme, Gemini key and model."""
        w = ctk.CTkToplevel(self)
        w.title("Settings")
        w.geometry("420x520")
        w.grab_set()   # modal: block the main window until closed
        vars_ = {}     # config key -> Tk variable

        def row(label, key, values=None, secret=False):
            """Add one labelled setting: a dropdown if values is given, else a text entry."""
            ctk.CTkLabel(w, text=label).pack(anchor="w", padx=20, pady=(10, 0))
            v = tk.StringVar(value=str(cfg[key]))
            vars_[key] = v
            (ctk.CTkOptionMenu(w, variable=v, values=values) if values
             else ctk.CTkEntry(w, textvariable=v, show="*" if secret else "")).pack(fill="x", padx=20)
        row("Learning language (OCR)", "lang", list(LANGS))
        row("Your language (translations)", "native", ["English", "Urdu", "Turkish", "Arabic", "Persian"])
        row("Level", "level", ["Beginner", "Elementary", "Intermediate", "Upper Intermediate", "Advanced"])
        row("Image batch limit", "batch_limit", ["5", "10", "20", "50", "100"])
        row("Theme", "theme", ["dark", "light"])
        row("Gemini API key (aistudio.google.com)", "api_key", secret=True)
        row("Gemini model", "model")

        def save():
            """Copy values into cfg, write config.json, apply theme, close the window."""
            for k, v in vars_.items():
                cfg[k] = int(v.get()) if k == "batch_limit" else v.get().strip()
            save_cfg()
            ctk.set_appearance_mode(cfg["theme"])
            self.refresh()
            w.destroy()
        ctk.CTkButton(w, text="Save Settings", command=save).pack(pady=20)


# ------------------------------------------------------------ 6. ENTRY POINT
if __name__ == "__main__":
    App().mainloop()  # create the window and start the Tk event loop
