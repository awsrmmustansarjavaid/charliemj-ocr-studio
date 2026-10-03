"""
editor.py - RichEditor: the 4th panel, a formatted text editor for the final study notes.

The OCR results flow into this editor automatically (Image N title -> main title ->
headings -> bullets). The user can then edit and format it before exporting.

How formatting works
    * Semantic tags describe WHAT the user chose:
        b i u s            bold, italic, underline, strike-through
        sz_<n>             explicit font size          fg_<hex> / bg_<hex>  text colour / highlight
        p_title p_h1 p_h2 p_h3   paragraph style       al_center / al_right  alignment
        li                 hanging indent for list lines
    * Tk cannot combine "bold" and "size" tags (a tag's font replaces the whole font), so
      restyle() adds ONE rendering tag per run, r_<bold><italic>_<size>, calculated from
      the semantic tags. Only the semantic tags are saved/exported.
    * get_blocks() / set_blocks() convert between the widget and richtext.Block lists,
      which every exporter uses.
"""
import re
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk

from . import richtext as rt
from .richtext import Block, Run

FAMILY = "Segoe UI"
GRAY = {"fg_color": "gray30"}
PURPLE = {"fg_color": "#6b46c1", "hover_color": "#805ad5"}
HIGHLIGHTS = {"Yellow": "#fff176", "Green": "#a5d6a7", "Pink": "#f8bbd0", "Blue": "#90caf9", "No highlight": ""}
STYLES = {"Normal": "normal", "Title": "title", "Heading 1": "h1", "Heading 2": "h2", "Heading 3": "h3"}
HR_TEXT = "─" * 34


class RichEditor(ctk.CTkFrame):
    """Formatted editor with toolbars, find/replace, list tools, AI buttons and exporters."""

    def __init__(self, master, ai_names=(), on_ai=None, on_update=None, on_focus=None, status=None):
        super().__init__(master)
        self.status = status or (lambda s: None)
        self.on_update, self.on_ai, self.on_focus = on_update, on_ai, on_focus
        self.base = 13                    # zoom: size of "normal" text
        self.dirty = False                # True once the user edits (stops automatic updates)
        self._loading = False
        self._rt = set()                  # rendering tags created so far
        self.auto = tk.BooleanVar(value=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # ---- toolbar row 1: style, inline formatting, size
        self.style_var = tk.StringVar(value="Normal")
        self.size_var = tk.StringVar(value="13")
        r1 = ctk.CTkFrame(self, fg_color="transparent")
        r1.grid(row=0, column=0, sticky="w", padx=6, pady=(6, 1))
        ctk.CTkOptionMenu(r1, variable=self.style_var, values=list(STYLES), width=104, height=28,
                          command=lambda v: self.set_style(STYLES[v])).pack(side="left", padx=2)
        for txt, tag, font in [("B", "b", ("Segoe UI", 13, "bold")), ("I", "i", ("Segoe UI", 13, "italic")),
                               ("U", "u", ("Segoe UI", 13, "underline")), ("S", "s", ("Segoe UI", 13, "overstrike"))]:
            ctk.CTkButton(r1, text=txt, width=30, height=28, font=font, command=lambda t=tag: self.toggle(t), **GRAY).pack(side="left", padx=1)
        ctk.CTkButton(r1, text="A−", width=32, height=28, command=lambda: self.bump(-2), **GRAY).pack(side="left", padx=(8, 1))
        ctk.CTkOptionMenu(r1, variable=self.size_var, width=62, height=28, values=["9", "10", "12", "13", "14", "16", "18", "20", "24", "28", "32", "40"],
                          command=lambda v: self.set_size(int(v))).pack(side="left", padx=1)
        ctk.CTkButton(r1, text="A+", width=32, height=28, command=lambda: self.bump(2), **GRAY).pack(side="left", padx=1)

        # ---- toolbar row 2: lists, alignment, colours
        r2 = ctk.CTkFrame(self, fg_color="transparent")
        r2.grid(row=1, column=0, sticky="w", padx=6, pady=1)
        for txt, cmd in [("• List", self.bullets), ("1. List", self.numbers), ("⬅", lambda: self.align("left")),
                         ("↔", lambda: self.align("center")), ("➡", lambda: self.align("right")),
                         ("🎨 Color", self.color), ("― Line", self.hr), ("Clear fmt", self.clear_format)]:
            ctk.CTkButton(r2, text=txt, width=44 if len(txt) < 3 else 66, height=28, command=cmd, **GRAY).pack(side="left", padx=1)
        self.hl_var = tk.StringVar(value="🖍 Highlight")
        ctk.CTkOptionMenu(r2, variable=self.hl_var, values=list(HIGHLIGHTS), width=104, height=28,
                          command=self.highlight).pack(side="left", padx=1)

        # ---- toolbar row 3: tools
        r3 = ctk.CTkFrame(self, fg_color="transparent")
        r3.grid(row=2, column=0, sticky="w", padx=6, pady=1)
        for txt, cmd in [("↶", lambda: self.safe(self.t.edit_undo)), ("↷", lambda: self.safe(self.t.edit_redo)),
                         ("🔍 Find", self.find_dialog), ("Sort A–Z", self.sort_bullets), ("No duplicates", self.dedupe),
                         ("⟳ Update from OCR", lambda: on_update and on_update()), ("⤺ Restore", self.restore)]:
            ctk.CTkButton(r3, text=txt, width=34 if len(txt) < 3 else 92, height=28, command=cmd,
                          **(PURPLE if "OCR" in txt else GRAY)).pack(side="left", padx=1)

        # ---- toolbar row 4: AI buttons (acting on the selection, or on the whole editor)
        r4 = ctk.CTkFrame(self, fg_color="transparent")
        r4.grid(row=3, column=0, sticky="w", padx=6, pady=1)
        for i, n in enumerate(ai_names):
            ctk.CTkButton(r4, text=n, width=84, height=26, command=lambda n=n: on_ai and on_ai(n), **PURPLE).grid(
                row=i // 4, column=i % 4, padx=1, pady=1)

        # Auto-update switch and Focus button sit to the right of the AI buttons (the toolbar rows above are full)
        ctk.CTkCheckBox(r4, text="Auto-update", variable=self.auto, width=20, checkbox_width=18, checkbox_height=18).grid(
            row=0, column=4, padx=(16, 2))
        ctk.CTkButton(r4, text="◀ Focus", width=84, height=26, command=lambda: on_focus and on_focus(), **GRAY).grid(
            row=1, column=4, padx=(16, 2))

        self.info = ctk.CTkLabel(self, text="", anchor="w", text_color="gray", font=("Segoe UI", 11))
        self.info.grid(row=4, column=0, sticky="ew", padx=10)

        # ---- the text area
        dark = ctk.get_appearance_mode() == "Dark"
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.grid(row=5, column=0, sticky="nsew", padx=6, pady=2)
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(0, weight=1)
        self.t = tk.Text(box, wrap="word", undo=True, maxundo=-1, bd=0, highlightthickness=0, padx=14, pady=10,
                         spacing1=2, spacing3=4, font=(FAMILY, 13), bg="#1e1e1e" if dark else "#ffffff",
                         fg="#e8e8e8" if dark else "#111111", insertbackground="#ffffff" if dark else "#000000",
                         selectbackground="#2b5fa8", selectforeground="#ffffff", inactiveselectbackground="#3a5a88")
        self.t.grid(row=0, column=0, sticky="nsew")
        sb = ctk.CTkScrollbar(box, command=self.t.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self.t.configure(yscrollcommand=sb.set)
        self._static_tags()

        # ---- footer: counters, copy and export
        ft = ctk.CTkFrame(self, fg_color="transparent")
        ft.grid(row=6, column=0, sticky="w", padx=6, pady=(2, 6))
        btns = [("Copy All", lambda: self.copy(rt.blocks_to_text(self.get_blocks()))), ("Copy Selected", self.copy_sel),
                ("Copy Markdown", lambda: self.copy(rt.blocks_to_md(self.get_blocks()))),
                ("Save .md", lambda: self.export("md")), ("TXT", lambda: self.export("txt")), ("HTML", lambda: self.export("html")),
                ("DOCX", lambda: self.export("docx")), ("CSV", lambda: self.export("csv"))]
        for i, (txt, cmd) in enumerate(btns):
            ctk.CTkButton(ft, text=txt, width=96 if len(txt) > 5 else 60, height=28, command=cmd).grid(row=i // 4, column=i % 4, padx=2, pady=2)

        # ---- bindings
        t = self.t
        t.bind("<<Modified>>", self._modified)
        t.bind("<KeyRelease>", self._key_release)
        t.bind("<Return>", self._enter)
        t.bind("<Control-b>", lambda e: (self.toggle("b"), "break")[1])
        t.bind("<Control-i>", lambda e: (self.toggle("i"), "break")[1])
        t.bind("<Control-u>", lambda e: (self.toggle("u"), "break")[1])
        t.bind("<Control-f>", lambda e: (self.find_dialog(), "break")[1])
        t.bind("<Control-MouseWheel>", lambda e: self.zoom(1 if e.delta > 0 else -1))
        t.bind("<Control-Button-4>", lambda e: self.zoom(1))
        t.bind("<Control-Button-5>", lambda e: self.zoom(-1))
        self._backup = None
        self.update_info()

    # ================================================================ tags and styling
    def _static_tags(self):
        t = self.t
        t.tag_configure("u", underline=True)
        t.tag_configure("s", overstrike=True)
        t.tag_configure("al_center", justify="center")
        t.tag_configure("al_right", justify="right")
        t.tag_configure("li", lmargin1=6, lmargin2=26)
        t.tag_configure("hr", foreground="#777777", justify="center")
        for st, sp in (("title", 14), ("h1", 12), ("h2", 10), ("h3", 8)):
            t.tag_configure("p_" + st, spacing1=sp, spacing3=4)
        t.tag_configure("found", background="#ffd54f", foreground="#000000")
        t.tag_raise("found")
        t.tag_raise("sel")

    def _dyn(self, name):
        """Create fg_<hex> / bg_<hex> tags on first use."""
        if name.startswith("fg_") and name not in self.t.tag_names():
            self.t.tag_configure(name, foreground="#" + name[3:])
        elif name.startswith("bg_") and name not in self.t.tag_names():
            self.t.tag_configure(name, background="#" + name[3:])
        return name

    def _rtag(self, bold, italic, size):
        name = f"r_{int(bold)}{int(italic)}_{size}"
        if name not in self._rt:
            self.t.tag_configure(name, font=(FAMILY, size, "bold" if bold else "normal", "italic" if italic else "roman"))
            self._rt.add(name)
        return name

    def _size(self, style, explicit):
        return explicit or max(8, round(rt.STYLE_SIZE[style] * self.base / 13))

    def _style(self, ln):
        return next((n[2:] for n in self.t.tag_names(f"{ln}.0") if n.startswith("p_")), "normal")

    def restyle(self, a=1, b=None):
        """Recalculate the rendering (font) tags of lines a..b from the semantic tags."""
        t = self.t
        last = int(t.index("end-1c").split(".")[0])
        for ln in range(max(1, a), (last if b is None else min(b, last)) + 1):
            for tg in self._rt:
                t.tag_remove(tg, f"{ln}.0", f"{ln}.end+1c")
            n = int(t.index(f"{ln}.end").split(".")[1])
            style, cur, start = self._style(ln), None, 0
            for k in range(n + 1):
                key = None
                if k < n:
                    names = t.tag_names(f"{ln}.{k}")
                    size = next((int(x[3:]) for x in names if x.startswith("sz_")), None)
                    key = ("b" in names or style in rt.STYLE_BOLD, "i" in names or style == "h3", self._size(style, size))
                if key != cur:
                    if cur is not None:
                        t.tag_add(self._rtag(*cur), f"{ln}.{start}", f"{ln}.{k}")
                    cur, start = key, k

    # ================================================================ blocks <-> widget
    def _run_tags(self, r):
        tags = [n for n, on in (("b", r.bold), ("i", r.italic), ("u", r.underline), ("s", r.strike)) if on]
        if r.size:
            tags.append(f"sz_{r.size}")
        if r.color:
            tags.append(self._dyn("fg_" + r.color.lstrip("#")))
        if r.bg:
            tags.append(self._dyn("bg_" + r.bg.lstrip("#")))
        return tuple(tags)

    def set_blocks(self, blocks):
        """Replace the whole document with these blocks."""
        t = self.t
        self._loading = True
        t.delete("1.0", "end")
        for n, b in enumerate(blocks):
            if n:
                t.insert("end-1c", "\n")
            ln = int(t.index("end-1c").split(".")[0])
            if b.hr:
                t.insert("end-1c", HR_TEXT, ("hr",))
                continue
            for r in b.runs:
                t.insert("end-1c", r.text, self._run_tags(r))
            if b.style != "normal":
                t.tag_add("p_" + b.style, f"{ln}.0", f"{ln}.end+1c")
            if b.align != "left":
                t.tag_add("al_" + b.align, f"{ln}.0", f"{ln}.end+1c")
            if re.match(r"^(• |\d+\. )", b.text):
                t.tag_add("li", f"{ln}.0", f"{ln}.end+1c")
        self.restyle()
        t.edit_modified(False)
        self._loading = False
        self.update_info()

    def load_blocks(self, blocks):
        """Load automatically generated content (keeps a backup of the previous text for 'Restore')."""
        if self.t.get("1.0", "end-1c").strip():
            self._backup = self.get_blocks()
        self.set_blocks(blocks)
        self.t.edit_reset()
        self.dirty = False

    def get_blocks(self):
        """Read the widget into a list of Blocks (one per line)."""
        t, blocks = self.t, []
        for ln in range(1, int(t.index("end-1c").split(".")[0]) + 1):
            text = t.get(f"{ln}.0", f"{ln}.end")
            names0 = t.tag_names(f"{ln}.0")
            if "hr" in names0 and text:
                blocks.append(Block(hr=True))
                continue
            align = "center" if "al_center" in names0 else "right" if "al_right" in names0 else "left"
            runs, cur, buf = [], None, ""
            for k, ch in enumerate(text):
                names = t.tag_names(f"{ln}.{k}")
                size = next((int(x[3:]) for x in names if x.startswith("sz_")), None)
                fg = next((x[3:] for x in names if x.startswith("fg_")), None)
                bg = next((x[3:] for x in names if x.startswith("bg_")), None)
                key = ("b" in names, "i" in names, "u" in names, "s" in names, size, fg, bg)
                if key != cur and buf:
                    runs.append(self._mk(buf, cur))
                    buf = ""
                cur, buf = key, buf + ch
            if buf:
                runs.append(self._mk(buf, cur))
            blocks.append(Block(self._style(ln), align, runs))
        return blocks

    @staticmethod
    def _mk(text, k):
        return Run(text, k[0], k[1], k[2], k[3], k[4], "#" + k[5] if k[5] else None, "#" + k[6] if k[6] else None)

    def restore(self):
        """Bring back the text that was replaced by the last automatic update."""
        if self._backup is None:
            return self.status("Nothing to restore")
        current = self.get_blocks()
        self.set_blocks(self._backup)
        self._backup, self.dirty = current, True
        self.status("✓ Previous editor text restored")

    # ================================================================ selection helpers
    def safe(self, fn):
        try:
            fn()
        except tk.TclError:
            pass

    def _sel(self):
        try:
            return self.t.index("sel.first"), self.t.index("sel.last")
        except tk.TclError:
            return None

    def _span(self):
        """Selection, else the word under the cursor, else the whole current line."""
        s = self._sel()
        if s:
            return s
        a, b = self.t.index("insert wordstart"), self.t.index("insert wordend")
        if a != b and self.t.get(a, b).strip():
            return a, b
        return self.t.index("insert linestart"), self.t.index("insert lineend")

    def _lines(self):
        a, b = self._sel() or (self.t.index("insert"), self.t.index("insert"))
        first, last = int(a.split(".")[0]), int(b.split(".")[0])
        if self._sel() and b.endswith(".0") and last > first:
            last -= 1
        return first, last

    def _touch(self, a=1, b=None):
        self.restyle(a, b)
        self.update_info()

    def _span_lines(self, a, b):
        return int(a.split(".")[0]), int(b.split(".")[0])

    # ================================================================ formatting commands
    def toggle(self, tag):
        a, b = self._span()
        if a == b:
            return self.status("Select some text first")
        idx, full = a, True
        while self.t.compare(idx, "<", b):
            if tag not in self.t.tag_names(idx):
                full = False
                break
            idx = self.t.index(f"{idx}+1c")
        (self.t.tag_remove if full else self.t.tag_add)(tag, a, b)
        self._touch(*self._span_lines(a, b))

    def set_size(self, n):
        a, b = self._span()
        for tg in self.t.tag_names():
            if tg.startswith("sz_"):
                self.t.tag_remove(tg, a, b)
        self.t.tag_add(f"sz_{n}", a, b)
        self._touch(*self._span_lines(a, b))

    def bump(self, d):
        a, _ = self._span()
        names = self.t.tag_names(a)
        cur = next((int(x[3:]) for x in names if x.startswith("sz_")), self._size(self._style(int(a.split(".")[0])), None))
        self.size_var.set(str(max(8, min(60, cur + d))))
        self.set_size(int(self.size_var.get()))

    def set_style(self, style):
        first, last = self._lines()
        for ln in range(first, last + 1):
            s, e = f"{ln}.0", f"{ln}.end+1c"
            for tg in self.t.tag_names():
                if tg.startswith("p_") or tg.startswith("sz_"):
                    self.t.tag_remove(tg, s, e)
            if style != "normal":
                self.t.tag_add("p_" + style, s, e)
        self._touch(first, last)

    def align(self, kind):
        first, last = self._lines()
        for ln in range(first, last + 1):
            for tg in ("al_center", "al_right"):
                self.t.tag_remove(tg, f"{ln}.0", f"{ln}.end+1c")
            if kind != "left":
                self.t.tag_add("al_" + kind, f"{ln}.0", f"{ln}.end+1c")

    def color(self):
        c = colorchooser.askcolor(parent=self, title="Text colour")[1]
        if c:
            a, b = self._span()
            for tg in self.t.tag_names():
                if tg.startswith("fg_"):
                    self.t.tag_remove(tg, a, b)
            self.t.tag_add(self._dyn("fg_" + c.lstrip("#")), a, b)

    def highlight(self, name):
        a, b = self._span()
        for tg in self.t.tag_names():
            if tg.startswith("bg_"):
                self.t.tag_remove(tg, a, b)
        if HIGHLIGHTS[name]:
            self.t.tag_add(self._dyn("bg_" + HIGHLIGHTS[name].lstrip("#")), a, b)
        self.hl_var.set("🖍 Highlight")

    def clear_format(self):
        a, b = self._span()
        for tg in self.t.tag_names():
            if tg in ("b", "i", "u", "s") or tg[:3] in ("sz_", "fg_", "bg_"):
                self.t.tag_remove(tg, a, b)
        self._touch(*self._span_lines(a, b))

    def hr(self):
        ln = int(self.t.index("insert").split(".")[0])
        self.t.insert(f"{ln}.end", "\n" + HR_TEXT, ("hr",))

    # ---- lists
    def _strip_prefix(self, ln):
        m = re.match(r"^(• |\d+\. )", self.t.get(f"{ln}.0", f"{ln}.end"))
        if m:
            self.t.delete(f"{ln}.0", f"{ln}.{len(m.group(1))}")
        return bool(m)

    def bullets(self):
        first, last = self._lines()
        all_on = all(self.t.get(f"{n}.0", f"{n}.end").startswith("• ") for n in range(first, last + 1))
        for ln in range(first, last + 1):
            self._strip_prefix(ln)
            self.t.tag_remove("li", f"{ln}.0", f"{ln}.end+1c")
            if not all_on:
                self.t.insert(f"{ln}.0", "• ")
                self.t.tag_add("li", f"{ln}.0", f"{ln}.end+1c")
        self._touch(first, last)

    def numbers(self):
        first, last = self._lines()
        all_on = all(re.match(r"^\d+\. ", self.t.get(f"{n}.0", f"{n}.end")) for n in range(first, last + 1))
        n = 0
        for ln in range(first, last + 1):
            self._strip_prefix(ln)
            self.t.tag_remove("li", f"{ln}.0", f"{ln}.end+1c")
            if not all_on and self.t.get(f"{ln}.0", f"{ln}.end").strip():
                n += 1
                self.t.insert(f"{ln}.0", f"{n}. ")
                self.t.tag_add("li", f"{ln}.0", f"{ln}.end+1c")
        self._touch(first, last)

    def sort_bullets(self):
        """Sort every bullet list alphabetically (A-Z)."""
        bl, out, i = self.get_blocks(), [], 0
        while i < len(bl):
            if bl[i].is_bullet:
                j = i
                while j < len(bl) and bl[j].is_bullet:
                    j += 1
                out += sorted(bl[i:j], key=lambda b: b.text[2:].casefold())
                i = j
            else:
                out.append(bl[i])
                i += 1
        self.set_blocks(out)
        self.dirty = True
        self.status("✓ Bullet lists sorted A–Z")

    def dedupe(self):
        """Remove repeated lines (same text, ignoring case) - e.g. the same word on several cards."""
        seen, out, removed = set(), [], 0
        for b in self.get_blocks():
            key = b.text.strip().casefold()
            if b.hr or not key or key not in seen:
                out.append(b)
                seen.add(key)
            else:
                removed += 1
        self.set_blocks(out)
        self.dirty = True
        self.status(f"✓ Removed {removed} duplicate line(s)")

    # ================================================================ typing behaviour
    def _enter(self, event):
        """Enter continues a list ('• ' / next number); Enter on an empty list item ends the list."""
        t = self.t
        if self._sel():
            return None
        ln = int(t.index("insert").split(".")[0])
        text = t.get(f"{ln}.0", f"{ln}.end")
        m = re.match(r"^(• |(\d+)\. )", text)
        if m and text.strip() in ("•", f"{m.group(2)}."):
            t.delete(f"{ln}.0", f"{ln}.end")
            t.tag_remove("li", f"{ln}.0", f"{ln}.end+1c")
            return "break"
        t.insert("insert", "\n")
        for tg in t.tag_names():
            if tg.startswith(("p_", "al_")) or tg == "li":
                t.tag_remove(tg, f"{ln + 1}.0", f"{ln + 1}.end+1c")
        if m:
            t.insert(f"{ln + 1}.0", "• " if m.group(1) == "• " else f"{int(m.group(2)) + 1}. ")
            t.tag_add("li", f"{ln + 1}.0", f"{ln + 1}.end+1c")
        self.restyle(ln, ln + 1)
        t.see("insert")
        return "break"

    def _key_release(self, event):
        ln = int(self.t.index("insert").split(".")[0])
        self.restyle(ln, ln)

    def _modified(self, event=None):
        if self.t.edit_modified():
            if not self._loading:
                self.dirty = True
            self.t.edit_modified(False)
            self.update_info()

    def zoom(self, d):
        self.base = max(9, min(30, self.base + d))
        self.restyle()
        self.status(f"Editor zoom: {self.base}")
        return "break"

    def update_info(self):
        txt = self.t.get("1.0", "end-1c")
        words = len(re.findall(r"\w+", txt))
        items = sum(1 for ln in txt.splitlines() if ln.startswith("• "))
        self.info.configure(text=f"{words} words · {len(txt.splitlines())} lines · {items} bullets"
                                 + ("   ✎ edited by you – OCR updates won't overwrite it" if self.dirty else ""))

    # ================================================================ find & replace
    def find_dialog(self):
        w = ctk.CTkToplevel(self)
        w.title("Find & Replace")
        w.geometry("380x250")
        w.attributes("-topmost", True)
        fv, rv, cv = tk.StringVar(), tk.StringVar(), tk.BooleanVar()
        for label, var in (("Find", fv), ("Replace with", rv)):
            ctk.CTkLabel(w, text=label).pack(anchor="w", padx=16, pady=(10, 0))
            ctk.CTkEntry(w, textvariable=var).pack(fill="x", padx=16)
        ctk.CTkCheckBox(w, text="Match case", variable=cv).pack(anchor="w", padx=16, pady=8)
        msg = ctk.CTkLabel(w, text="", text_color="gray")
        self.t.mark_set("findpos", "1.0")

        def nxt():
            self.t.tag_remove("found", "1.0", "end")
            if not fv.get():
                return None
            for start in (self.t.index("findpos"), "1.0"):
                pos = self.t.search(fv.get(), start, "end", nocase=not cv.get())
                if pos:
                    end = f"{pos}+{len(fv.get())}c"
                    self.t.tag_add("found", pos, end)
                    self.t.see(pos)
                    self.t.mark_set("findpos", end)
                    msg.configure(text="")
                    return pos
            msg.configure(text="Not found")
            return None

        def rep():
            r = self.t.tag_ranges("found")
            if r:
                self.t.delete(r[0], r[1])
                self.t.insert(r[0], rv.get())
                self.restyle(int(str(r[0]).split(".")[0]), int(str(r[0]).split(".")[0]))
            nxt()

        def rep_all():
            n, idx = 0, "1.0"
            while fv.get():
                pos = self.t.search(fv.get(), idx, "end", nocase=not cv.get())
                if not pos:
                    break
                self.t.delete(pos, f"{pos}+{len(fv.get())}c")
                self.t.insert(pos, rv.get())
                idx, n = f"{pos}+{len(rv.get())}c", n + 1
            self.restyle()
            msg.configure(text=f"Replaced {n}")
        row = ctk.CTkFrame(w, fg_color="transparent")
        row.pack(pady=4)
        for txt, cmd in (("Find next", nxt), ("Replace", rep), ("Replace all", rep_all)):
            ctk.CTkButton(row, text=txt, width=108, command=cmd).pack(side="left", padx=3)
        msg.pack()
        w.bind("<Return>", lambda e: nxt())
        w.bind("<Destroy>", lambda e: self.t.tag_remove("found", "1.0", "end") if e.widget is w else None)

    # ================================================================ AI integration
    def selection_text(self):
        """(text, (first_line, last_line) or None): the selected lines, else the whole document as Markdown."""
        s = self._sel()
        if s:
            first, last = self._lines()
            blocks = self.get_blocks()[first - 1:last]
            return rt.blocks_to_text(blocks), (first, last)
        return rt.blocks_to_md(self.get_blocks()), None

    def apply_ai(self, md, mode, lines):
        """Put an AI answer into the document: replace the selected lines / everything, or append."""
        blocks = self.get_blocks()
        new = rt.md_to_blocks(md, top="h1" if lines else "title")
        if mode == "append":
            blocks += new
        elif lines:
            blocks = blocks[:lines[0] - 1] + new + blocks[lines[1]:]
        else:
            blocks = new
        self.set_blocks(blocks)
        self.dirty = True

    # ================================================================ copy and export
    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status("✓ Copied to clipboard")

    def copy_sel(self):
        s = self._sel()
        if s:
            self.copy(self.t.get(*s))
        else:
            self.status("Select some text first")

    def export(self, kind):
        """Save the editor content as md / txt / html / docx / csv."""
        path = filedialog.asksaveasfilename(defaultextension="." + kind, filetypes=[(kind.upper(), "*." + kind)])
        if not path:
            return
        self.write(path, kind)
        self.status(f"✓ Saved {path.replace(chr(92), '/').split('/')[-1]}")

    def write(self, path, kind):
        """Write the document to `path` (also used by the automated tests)."""
        blocks = self.get_blocks()
        if kind == "docx":
            return rt.write_docx(path, blocks)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:      # BOM: Excel shows Turkish/Urdu correctly
            if kind == "md":
                f.write(rt.blocks_to_md(blocks))
            elif kind == "txt":
                f.write(rt.blocks_to_text(blocks))
            elif kind == "html":
                f.write(rt.blocks_to_html(blocks))
            else:
                import csv
                w, seen = csv.writer(f), set()
                w.writerow(["Image", "Original", "Translation"])
                for img, a, b in rt.blocks_pairs(blocks):
                    if a.lower() not in seen:
                        seen.add(a.lower())
                        w.writerow([img, a, b])
