"""
selector.py - the "Select Area" tool: a small image viewer / editor for choosing what to OCR.

    Zoom     − / +  buttons, Ctrl + mouse wheel (zooms at the pointer), keys + - 0 1
    Fit      whole image in the window (the default)      Fit width      100 %
    Pan      right / middle mouse drag, mouse wheel (Shift = sideways), arrow keys, scroll bars
    Select   drag a box with the left button - as many boxes as you like
    Send to  "This image"  : the text is ADDED to the result of the image you opened this from
             "New image"   : the box becomes a new image in the queue
             "Crop image"  : the picture itself is cropped to the box
    Edit     rotate left / right, undo the last crop or rotation

Speed: only the VISIBLE part of the picture is cut out of the original and scaled, so even a huge
screenshot zooms and pans instantly. Boxes are kept in original-image pixels, so zooming never moves
them, and OCR always works on the full-resolution original.
"""
import tkinter as tk

from PIL import Image, ImageTk


class AreaSelector(tk.Toplevel):
    """Window for drawing selection boxes on an image."""

    def __init__(self, master, image, on_select, on_replace=None):
        super().__init__(master)
        self.src = image.convert("RGB")
        self.on_select, self.on_replace = on_select, on_replace
        self.k, self.ox, self.oy = 1.0, 0.0, 0.0        # scale, and the image point shown in the top-left corner
        self.marks, self.hist, self.n = [], [], 0         # drawn boxes (image pixels), undo history, box counter
        self.target = tk.StringVar(value="same")
        self.msg = tk.StringVar(value="Drag a box around the text. Right-drag pans, Ctrl+wheel zooms.")
        self._rect = self._start = self._pan = None
        self._pending = False
        self.title("Select area(s) to OCR")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{int(sw * 0.88)}x{int(sh * 0.86)}+{int(sw * 0.06)}+{int(sh * 0.04)}")

        bar = tk.Frame(self)
        bar.pack(fill="x", padx=4, pady=3)
        for txt, cmd in [("−", lambda: self.zoom(1 / 1.25)), ("+", lambda: self.zoom(1.25)), ("Fit", self.fit),
                         ("Fit width", self.fit_width), ("100%", self.actual), ("⟲", lambda: self.rotate(90)),
                         ("⟳", lambda: self.rotate(-90)), ("↶ Undo edit", self.undo_edit), ("Clear marks", self.clear_marks)]:
            tk.Button(bar, text=txt, command=cmd, width=2 if len(txt) < 3 else 0, padx=6).pack(side="left", padx=2)
        tk.Button(bar, text="Done", command=self.destroy, padx=10).pack(side="right", padx=2)
        self.zoom_lbl = tk.Label(bar, width=7)
        self.zoom_lbl.pack(side="right")
        bar2 = tk.Frame(self)
        bar2.pack(fill="x", padx=4)
        tk.Label(bar2, text="OCR result goes to:").pack(side="left")
        for txt, val in (("This image", "same"), ("New image", "new"), ("Crop the image instead", "crop")):
            tk.Radiobutton(bar2, text=txt, variable=self.target, value=val).pack(side="left", padx=6)
        tk.Label(self, textvariable=self.msg, anchor="w", fg="#2b6cb0").pack(fill="x", padx=6)

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

        cv = self.cv
        cv.bind("<ButtonPress-1>", self._press)
        cv.bind("<B1-Motion>", self._drag)
        cv.bind("<ButtonRelease-1>", self._release)
        for b in (2, 3):
            cv.bind(f"<ButtonPress-{b}>", self._pan_start)
            cv.bind(f"<B{b}-Motion>", self._pan_move)
        cv.bind("<MouseWheel>", self._wheel)
        cv.bind("<Button-4>", lambda e: self._wheel(e, 1))
        cv.bind("<Button-5>", lambda e: self._wheel(e, -1))
        cv.bind("<Configure>", lambda e: self.schedule())
        for key, fn in (("<plus>", lambda e: self.zoom(1.25)), ("<equal>", lambda e: self.zoom(1.25)), ("<minus>", lambda e: self.zoom(1 / 1.25)),
                        ("0", lambda e: self.fit()), ("1", lambda e: self.actual()), ("<Escape>", lambda e: self.destroy()),
                        ("<Left>", lambda e: self.pan(-60, 0)), ("<Right>", lambda e: self.pan(60, 0)),
                        ("<Up>", lambda e: self.pan(0, -60)), ("<Down>", lambda e: self.pan(0, 60))):
            self.bind(key, fn)
        self.transient(master)
        self.after(120, self._ready)

    def _ready(self):
        try:
            self.grab_set()
            self.focus_set()
        except tk.TclError:
            pass
        self.fit()

    # ------------------------------------------------------------------ view
    def view(self):
        """Size of the visible canvas area in pixels."""
        return max(60, self.cv.winfo_width()), max(60, self.cv.winfo_height())

    def schedule(self):
        """Redraw soon (several requests in a row are merged into one redraw)."""
        if not self._pending:
            self._pending = True
            self.after(12, self.render)

    def render(self):
        """Draw the visible part of the picture, the boxes and update the scroll bars."""
        self._pending = False
        W, H = self.src.size
        cw, ch = self.view()
        k = self.k
        vw, vh = cw / k, ch / k
        self.ox = (W - vw) / 2 if vw >= W else min(max(self.ox, 0), W - vw)        # keep the picture on screen / centred
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
        self.vs.set(max(0, self.oy) / H, min(1, (self.oy + vh) / H))
        self.hs.set(max(0, self.ox) / W, min(1, (self.ox + vw) / W))
        self.zoom_lbl.configure(text=f"{k * 100:.0f}%")

    def to_cv(self, ix, iy):
        return (ix - self.ox) * self.k, (iy - self.oy) * self.k

    def to_img(self, cx, cy):
        return self.ox + cx / self.k, self.oy + cy / self.k

    def zoom(self, f, cx=None, cy=None):
        """Zoom by factor f around the pointer (or the centre)."""
        cw, ch = self.view()
        cx, cy = (cw / 2 if cx is None else cx), (ch / 2 if cy is None else cy)
        ix, iy = self.to_img(cx, cy)
        self.k = min(8.0, max(0.03, self.k * f))
        self.ox, self.oy = ix - cx / self.k, iy - cy / self.k                    # the point under the pointer stays put
        self.schedule()

    def fit(self):
        W, H = self.src.size
        cw, ch = self.view()
        self.k, self.ox, self.oy = min(cw / W, ch / H, 1.0), 0, 0
        self.schedule()

    def fit_width(self):
        W, _ = self.src.size
        self.k, self.ox, self.oy = min(self.view()[0] / W, 4.0), 0, 0
        self.schedule()

    def actual(self):
        self.k = 1.0
        self.schedule()

    def pan(self, dx, dy):
        self.ox, self.oy = self.ox + dx / self.k, self.oy + dy / self.k
        self.schedule()

    def _scroll(self, axis, *a):
        """Scroll-bar commands."""
        W, H = self.src.size
        size, pos = (H, "oy") if axis == "y" else (W, "ox")
        if a[0] == "moveto":
            setattr(self, pos, float(a[1]) * size)
        else:
            step = (self.view()[1 if axis == "y" else 0] / self.k) * (0.9 if a[2] == "pages" else 0.1)
            setattr(self, pos, getattr(self, pos) + int(a[1]) * step)
        self.schedule()

    def _wheel(self, e, d=None):
        d = d if d is not None else (1 if e.delta > 0 else -1)
        if e.state & 0x4:                                                         # Ctrl: zoom at the pointer
            self.zoom(1.2 if d > 0 else 1 / 1.2, e.x, e.y)
        elif e.state & 0x1:                                                       # Shift: sideways
            self.pan(-d * 80, 0)
        else:
            self.pan(0, -d * 80)

    def _pan_start(self, e):
        self._pan = (e.x, e.y)

    def _pan_move(self, e):
        if self._pan:
            self.pan(self._pan[0] - e.x, self._pan[1] - e.y)
            self._pan = (e.x, e.y)

    # ------------------------------------------------------------------ selecting
    def _press(self, e):
        self._start = (e.x, e.y)
        self._rect = self.cv.create_rectangle(e.x, e.y, e.x, e.y, outline="#00aaff", width=2, dash=(4, 2))

    def _drag(self, e):
        if self._rect is not None:
            self.cv.coords(self._rect, *self._start, e.x, e.y)

    def _release(self, e):
        if self._rect is None:
            return
        self.cv.delete(self._rect)
        self._rect = None
        (ax, ay), (bx, by) = self.to_img(*self._start), self.to_img(e.x, e.y)
        W, H = self.src.size
        box = (max(0, min(ax, bx)), max(0, min(ay, by)), min(W, max(ax, bx)), min(H, max(ay, by)))
        if abs(e.x - self._start[0]) < 8 or abs(e.y - self._start[1]) < 8 or box[2] - box[0] < 4 or box[3] - box[1] < 4:
            return                                                                # an accidental click, not a box
        self.commit(box)

    def commit(self, box):
        """Cut the box out of the ORIGINAL picture and send it where the user chose."""
        crop = self.src.crop(tuple(int(v) for v in box))
        target = self.target.get()
        if target == "crop":
            self._edit(crop)
            self.msg.set(f"Image cropped to {crop.width}×{crop.height} px  (↶ Undo edit brings the old picture back)")
            return
        self.n += 1
        ok = self.on_select(crop, self.n, target)
        if ok is False:
            self.n -= 1
            self.msg.set("⚠ Could not add the area (batch limit reached?)")
            return
        self.marks.append((box, self.n))
        self.msg.set(f"✓ Area {self.n} sent to {'this image' if target == 'same' else 'a new image'} - OCR is running")
        self.schedule()

    # ------------------------------------------------------------------ editing
    def _edit(self, new, remember=True):
        """Replace the working picture (crop / rotate), tell the app and start fresh."""
        if remember:
            self.hist.append(self.src)
        self.src = new
        self.marks = []
        if self.on_replace:
            self.on_replace(new)
        self.fit()

    def rotate(self, angle):
        self._edit(self.src.rotate(angle, expand=True))
        self.msg.set("Rotated")

    def undo_edit(self):
        if self.hist:
            self._edit(self.hist.pop(), remember=False)
            self.msg.set("Edit undone")

    def clear_marks(self):
        self.marks = []
        self.schedule()
