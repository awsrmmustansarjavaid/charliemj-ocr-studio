from __future__ import annotations

import tkinter as tk
from PIL import Image, ImageTk


class AreaSelector(tk.Toplevel):
    """Interactive screenshot selector with zoom, pan, undo/redo and rotation."""

    def __init__(self, master, image, callback):
        super().__init__(master)
        self.title("Select OCR areas")
        self.callback = callback
        self.src = image.copy()
        self.k = 1.0
        self.ox = 0.0
        self.oy = 0.0
        self.marks = []
        self.undo_stack = []
        self.redo_stack = []
        self.drag_start = None
        self.pan_start = None
        self._build_ui()
        self._redraw()

    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill="x")
        for text, command in (
            ("Undo", self.undo), ("Redo", self.redo), ("Rotate", self.rotate),
            ("+", lambda: self.zoom(1.2)), ("-", lambda: self.zoom(1 / 1.2)),
        ):
            tk.Button(top, text=text, command=command).pack(side="left", padx=2, pady=2)
        tk.Button(top, text="Done", command=self.finish).pack(side="right", padx=4, pady=2)

        self.zoom_lbl = tk.Label(top, text="100%")
        self.zoom_lbl.pack(side="right", padx=8)

        body = tk.Frame(self)
        body.pack(fill="both", expand=True)
        self.vs = tk.Scrollbar(body, orient="vertical")
        self.hs = tk.Scrollbar(body, orient="horizontal")
        self.cv = tk.Canvas(body, background="black", highlightthickness=0,
                            xscrollcommand=self.hs.set, yscrollcommand=self.vs.set)
        self.hs.configure(command=self._xview)
        self.vs.configure(command=self._yview)
        self.vs.pack(side="right", fill="y")
        self.hs.pack(side="bottom", fill="x")
        self.cv.pack(side="left", fill="both", expand=True)
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<ButtonPress-3>", self._pan_press)
        self.cv.bind("<B3-Motion>", self._pan_drag)
        self.cv.bind("<MouseWheel>", self._wheel)

    def view(self):
        cw = max(1, self.cv.winfo_width())
        ch = max(1, self.cv.winfo_height())
        return cw, ch

    def _redraw(self):
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
        self.vs.set(max(0, self.oy) / H, min(1, (self.oy + vh) / H))
        self.hs.set(max(0, self.ox) / W, min(1, (self.ox + vw) / W))
        self.zoom_lbl.configure(text=f"{k * 100:.0f}%")

    def to_cv(self, ix, iy):
        return (ix - self.ox) * self.k, (iy - self.oy) * self.k

    def to_img(self, cx, cy):
        return self.ox + cx / self.k, self.oy + cy / self.k

    def zoom(self, f, cx=None, cy=None):
        cw, ch = self.view()
        cx = cw / 2 if cx is None else cx
        cy = ch / 2 if cy is None else cy
        ix, iy = self.to_img(cx, cy)
        self.k = min(8.0, max(0.03, self.k * f))
        self.ox = ix - cx / self.k
        self.oy = iy - cy / self.k
        self._redraw()

    def _wheel(self, event):
        self.zoom(1.1 if event.delta > 0 else 1 / 1.1, event.x, event.y)

    def _xview(self, *args):
        if args and args[0] == "moveto":
            W, H = self.src.size
            cw, ch = self.view()
            self.ox = float(args[1]) * W
            self.ox = max(0, min(self.ox, max(0, W - cw / self.k)))
            self._redraw()
        elif args and args[0] == "scroll":
            self.ox += float(args[1]) * 40 / self.k
            self._redraw()

    def _yview(self, *args):
        if args and args[0] == "moveto":
            W, H = self.src.size
            cw, ch = self.view()
            self.oy = float(args[1]) * H
            self.oy = max(0, min(self.oy, max(0, H - ch / self.k)))
            self._redraw()
        elif args and args[0] == "scroll":
            self.oy += float(args[1]) * 40 / self.k
            self._redraw()

    def _press(self, event):
        x, y = self.to_img(event.x, event.y)
        self.drag_start = (x, y)

    def _drag(self, event):
        if not self.drag_start:
            return
        self._redraw()
        x0, y0 = self.to_cv(*self.drag_start)
        x1, y1 = event.x, event.y
        self.cv.create_rectangle(x0, y0, x1, y1, outline="#f59e0b", width=2)

    def _release(self, event):
        if not self.drag_start:
            return
        x0, y0 = self.drag_start
        x1, y1 = self.to_img(event.x, event.y)
        W, H = self.src.size
        box = (max(0, min(x0, x1)), max(0, min(y0, y1)),
               min(W, max(x0, x1)), min(H, max(y0, y1)))
        if box[2] - box[0] >= 2 and box[3] - box[1] >= 2:
            self.undo_stack.append(list(self.marks))
            self.redo_stack.clear()
            self.marks.append((box, len(self.marks) + 1))
        self.drag_start = None
        self._redraw()

    def _pan_press(self, event):
        self.pan_start = (event.x, event.y, self.ox, self.oy)

    def _pan_drag(self, event):
        if not self.pan_start:
            return
        sx, sy, ox, oy = self.pan_start
        self.ox = ox - (event.x - sx) / self.k
        self.oy = oy - (event.y - sy) / self.k
        self._redraw()

    def undo(self):
        if self.marks:
            self.redo_stack.append(list(self.marks))
            self.marks = self.undo_stack.pop() if self.undo_stack else []
            self._redraw()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(list(self.marks))
            self.marks = self.redo_stack.pop()
            self._redraw()

    def rotate(self):
        self.src = self.src.rotate(90, expand=True)
        self.marks = []
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.ox = self.oy = 0
        self._redraw()

    def finish(self):
        boxes = [box for box, _ in self.marks]
        if self.callback:
            self.callback(boxes)
        self.destroy()
