"""Image-area selector with zoom, pan, multi-selection and undo/redo.

Selections are always stored in original-image pixels, so zooming never changes
what is sent to OCR.  Selection history is separate from crop/rotate edit
history: users can undo/redo boxes without losing image edits.
"""
import tkinter as tk
from PIL import Image, ImageTk


class AreaSelector(tk.Toplevel):
    """Window for drawing, removing and undoing OCR selection boxes."""

    def __init__(self, master, image, on_select, on_replace=None):
        super().__init__(master)
        self.src = image.convert("RGB")
        self.on_select, self.on_replace = on_select, on_replace
        self.k, self.ox, self.oy = 1.0, 0.0, 0.0
        self.marks, self.hist, self.n = [], [], 0
        self.selection_undo, self.selection_redo = [], []
        self.target = tk.StringVar(value="same")
        self.msg = tk.StringVar(value="Drag a box around the text. Right-drag pans, Ctrl+wheel zooms.")
        self._rect = self._start = self._pan = None
        self._pending = False
        self.title("Select area(s) to OCR")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{int(sw * 0.88)}x{int(sh * 0.86)}+{int(sw * 0.06)}+{int(sh * 0.04)}")

        bar = tk.Frame(self)
        bar.pack(fill="x", padx=4, pady=3)
        controls = [
            ("−", lambda: self.zoom(1 / 1.25)), ("+", lambda: self.zoom(1.25)),
            ("Fit", self.fit), ("Fit width", self.fit_width), ("100%", self.actual),
            ("⟲", lambda: self.rotate(90)), ("⟳", lambda: self.rotate(-90)),
            ("↶ Undo edit", self.undo_edit), ("↶ Undo box", self.undo_selection),
            ("↷ Redo box", self.redo_selection), ("Delete box", self.delete_selected),
            ("Clear marks", self.clear_marks),
        ]
        for txt, cmd in controls:
            tk.Button(bar, text=txt, command=cmd, padx=5).pack(side="left", padx=1)
        tk.Button(bar, text="Done", command=self.destroy, padx=10).pack(side="right", padx=2)
        self.zoom_lbl = tk.Label(bar, width=7)
        self.zoom_lbl.pack(side="right")
        bar2 = tk.Frame(self)
        bar2.pack(fill="x", padx=4)
        tk.Label(bar2, text="OCR result goes to:").pack(side="left")
        for txt, val in (("This image", "same"), ("New image", "new"), ("Crop the image instead", "crop")):
            tk.Radiobutton(bar2, text=txt, variable=self.target, value=val).pack(side="left", padx=6)
        tk.Label(self, textvariable=self.msg, anchor="w").pack(fill="x", padx=6)

        body = tk.Frame(self)
        body.pack(fill="both", expand=True)
        self.cv = tk.Canvas(body, bg="#222222", highlightthickness=0, cursor="cross")
        self.vs = tk.Scrollbar(body, orient="vertical", command=lambda *a: self._scroll("y", *a))
        self.hs = tk.Scrollbar(body, orient="horizontal", command=lambda *a: self._scroll("x", *a))
        self.cv.grid(row=0, column=0, sticky="nsew")
        self.vs.grid(row=0, column=1, sticky="ns")
        self.hs.grid(row=1, column=0, sticky="ew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<Button-3>", self._right_click)
        for b in (2,):
            self.cv.bind(f"<ButtonPress-{b}>", self._pan_start)
            self.cv.bind(f"<B{b}-Motion>", self._pan_move)
        self.cv.bind("<MouseWheel>", self._wheel)
        self.cv.bind("<Button-4>", lambda e: self._wheel(e, 1))
        self.cv.bind("<Button-5>", lambda e: self._wheel(e, -1))
        self.cv.bind("<Configure>", lambda e: self.schedule())
        for key, fn in (("<plus>", lambda e: self.zoom(1.25)), ("<equal>", lambda e: self.zoom(1.25)),
                        ("<minus>", lambda e: self.zoom(1 / 1.25)), ("0", lambda e: self.fit()),
                        ("1", lambda e: self.actual()), ("<Escape>", lambda e: self.destroy()),
                        ("<Left>", lambda e: self.pan(-60, 0)), ("<Right>", lambda e: self.pan(60, 0)),
                        ("<Up>", lambda e: self.pan(0, -60)), ("<Down>", lambda e: self.pan(0, 60)),
                        ("<Control-z>", lambda e: self.undo_selection()), ("<Control-y>", lambda e: self.redo_selection()),
                        ("<Delete>", lambda e: self.delete_selected())):
            self.bind(key, fn)
        self.transient(master)
        self.after(120, self._ready)

    def _ready(self):
        try:
            self.grab_set(); self.focus_set()
        except tk.TclError:
            pass
        self.fit()

    def view(self):
        """Return the visible canvas dimensions."""
        return max(60, self.cv.winfo_width()), max(60, self.cv.winfo_height())

    def schedule(self):
        """Coalesce redraw requests for smooth panning and zooming."""
        if not self._pending:
            self._pending = True
            self.after(12, self.render)

    def render(self):
        """Draw the visible source region and selection boxes."""
        self._pending = False
        W, H = self.src.size
        cw, ch = self.view()
        k = self.k
        vw, vh = cw / k, ch / k
        self.ox = (W - vw) / 2 if vw >= W else min(max(self.ox, 0), W - vw)
        self.oy = (H - vh) / 2 if vh >= H else min(max(self.oy, 0), H - vh)
        x0, y0 = max(0, int(self.ox)), max(0, int(self.oy))
        x1, y1 = min(W, int(self.ox + vw) + 2), min(H, int(self.oy + vh) + 2)
        region = self.src.crop((x0, y0, x1, y1))
        img = region.resize((max(1, round(region.width * k)), max(1, round(region.height * k))), Image.BILINEAR)
        self.photo = ImageTk.PhotoImage(img)
        self.cv.delete("all")
        self.cv.create_image(round((x0 - self.ox) * k), round((y0 - self.oy) * k), image=self.photo, anchor="nw")
        for (bx0, by0, bx1, by1), n in self.marks:
            a, b = self.to_cv(bx0, by0), self.to_cv(bx1, by1)
            self.cv.create_rectangle(*a, *b, outline="#22c55e", width=2)
            self.cv.create_text(a[0] + 6, a[1] + 4, text=str(n), fill="#22c55e", anchor="nw", font=("Segoe UI", 14, "bold"))
        self.vs.set(max(0, self.oy) / H, min(1, (self.oy + vh) / H)
        self.hs.set(max(0, self.ox) / W, min(1, (self.ox + vw) / W)
        self.zoom_lbl.configure(text=f"{k * 100:.0f}%")

    def to_cv(self, ix, iy):
        return (ix - self.ox) * self.k, (iy - self.oy) * self.k

    def to_img(self, cx, cy):
        return self.ox + cx / self.k, self.oy + cy / self.k

    def zoom(self, f, cx=None, cy=None):
        """Zoom around the pointer while keeping that image point fixed."""
        cw, ch = self.view(); cx = cw / 2 if cx is None else cx; cy = ch / 2 if cy is None else cy
        ix, iy = self.to_img(cx, cy)
        self.k = min(8.0, max(0.03, self.k * f))
        self.ox, self.oy = ix - cx / self.k, iy - cy / self.k
        self.schedule()

    def fit(self):
        """Fit the complete source image in the viewer."""
        W, H = self.src.size; cw, ch = self.view()
        self.k, self.ox, self.oy = min(cw / W, ch / H, 1.0), 0, 0; self.schedule()

    def fit_width(self):
        """Fit the image width to the viewer."""
        W, _ = self.src.size; self.k, self.ox, self.oy = min(self.view()[0] / W, 4.0), 0, 0; self.schedule()

    def actual(self):
        """Show source pixels at 100 percent."""
        self.k = 1.0; self.schedule()

    def pan(self, dx, dy):
        """Pan by screen pixels."""
        self.ox, self.oy = self.ox + dx / self.k, self.oy + dy / self.k; self.schedule()

    def _scroll(self, axis, *a):
        """Handle scrollbar movement."""
        W, H = self.src.size; size, pos = (H, "oy") if axis == "y" else (W, "ox")
        if a[0] == "moveto":
            setattr(self, pos, float(a[1]) * size)
        else:
            step = self.view()[1 if axis == "y" else 0] / self.k * (0.9 if a[2] == "pages" else 0.1)
            setattr(self, pos, getattr(self, pos) + int(a[1]) * step)
        self.schedule()

    def _wheel(self, e, d=None):
        """Zoom with Ctrl-wheel, pan otherwise."""
        d = d if d is not None else (1 if e.delta > 0 else -1)
        if e.state & 0x4: self.zoom(1.2 if d > 0 else 1 / 1.2, e.x, e.y)
        elif e.state & 0x1: self.pan(-d * 80, 0)
        else: self.pan(0, -d * 80)

    def _pan_start(self, e): self._pan = (e.x, e.y)

    def _pan_move(self, e):
        if self._pan:
            self.pan(self._pan[0] - e.x, self._pan[1] - e.y); self._pan = (e.x, e.y)

    def _press(self, e):
        """Start a new selection box."""
        self._start = (e.x, e.y)
        self._rect = self.cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2, dash=(4, 2))

    def _drag(self, e):
        if self._rect is not None: self.cv.coords(self._rect, *self._start, e.x, e.y)

    def _release(self, e):
        if self._rect is None: return
        self.cv.delete(self._rect); self._rect = None
        (ax, ay), (bx, by) = self.to_img(*self._start), self.to_img(e.x, e.y)
        W, H = self.src.size
        box = (max(0, min(ax, bx)), max(0, min(ay, by)), min(W, max(ax, bx)), min(H, max(ay, by)))
        if abs(e.x - self._start[0]) < 8 or abs(e.y - self._start[1]) < 8 or box[2] - box[0] < 4 or box[3] - box[1] < 4: return
        self.commit(box)

    def _right_click(self, e):
        """Right-click the nearest box to remove it without changing the image."""
        ix, iy = self.to_img(e.x, e.y)
        hit = None
        for idx, (box, _) in enumerate(self.marks):
            x0, y0, x1, y1 = box
            if x0 <= ix <= x1 and y0 <= iy <= y1:
                hit = idx; break
        if hit is not None: self._remove_mark(hit)

    def _snapshot(self):
        """Return an immutable selection-list snapshot."""
        return tuple((tuple(box), n) for box, n in self.marks)

    def _restore(self, snap):
        self.marks = [(tuple(box), n) for box, n in snap]
        self.schedule()

    def _record_selection_change(self, before):
        after = self._snapshot()
        if before != after:
            self.selection_undo.append(before)
            self.selection_redo.clear()

    def commit(self, box):
        """OCR a box and add it to the selection history."""
        crop = self.src.crop(tuple(int(v) for v in box)); target = self.target.get()
        if target == "crop":
            self._edit(crop); self.msg.set(f"Image cropped to {crop.width}×{crop.height} px"); return
        self.n += 1
        ok = self.on_select(crop, self.n, target)
        if ok is False:
            self.n -= 1; self.msg.set("⚠ Could not add the area (batch limit reached?)"); return
        before = self._snapshot()
        self.marks.append((box, self.n)); self._record_selection_change(before)
        self.msg.set(f"✓ Area {self.n} sent to {'this image' if target == 'same' else 'a new image'} - OCR is running")
        self.schedule()

    def _remove_mark(self, index):
        """Remove one selection box and record it for undo."""
        if not 0 <= index < len(self.marks): return
        before = self._snapshot(); self.marks.pop(index); self._record_selection_change(before)
        self.msg.set("Selection removed. Ctrl+Z restores it.")

    def delete_selected(self):
        """Delete the most recently added selection when no pointer hit is known."""
        if self.marks: self._remove_mark(len(self.marks) - 1)

    def undo_selection(self):
        """Undo the last selection add/remove operation."""
        if not self.selection_undo: return
        self.selection_redo.append(self._snapshot()); self._restore(self.selection_undo.pop())
        self.msg.set("Selection undone")

    def redo_selection(self):
        """Redo the last undone selection operation."""
        if not self.selection_redo: return
        self.selection_undo.append(self._snapshot()); self._restore(self.selection_redo.pop())
        self.msg.set("Selection redone")

    def _edit(self, new, remember=True):
        """Replace the working picture for crop/rotate and keep edit history."""
        if remember: self.hist.append(self.src)
        self.src = new; self.marks = []; self.selection_undo.clear(); self.selection_redo.clear()
        if self.on_replace: self.on_replace(new)
        self.fit()

    def rotate(self, angle):
        """Rotate the working image."""
        self._edit(self.src.rotate(angle, expand=True)); self.msg.set("Rotated")

    def undo_edit(self):
        """Undo the most recent crop/rotation."""
        if self.hist:
            self._edit(self.hist.pop(), remember=False); self.msg.set("Edit undone")

    def clear_marks(self):
        """Clear all boxes as one undoable operation."""
        if not self.marks: return
        before = self._snapshot(); self.marks = []; self._record_selection_change(before); self.msg.set("All selections cleared")
        self.schedule()
