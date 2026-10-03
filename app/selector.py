"""
selector.py - the "Select Area" tool.

Opens the chosen image in its own window (fitted to the screen width, scrollable) and lets
the user drag boxes around the text they want. Every box is cut out of the ORIGINAL image
at full resolution and handed to a callback - the main window adds it to the queue as a new
"Image N" and OCRs it. Several boxes can be drawn one after another; Esc or "Done" closes.

Plain tkinter widgets are used on purpose: they behave the same in light and dark themes
and keep the tool small.
"""
import tkinter as tk

from PIL import Image, ImageTk


class AreaSelector(tk.Toplevel):
    """Modal window for drawing selection boxes on an image."""

    def __init__(self, master, image, on_select):
        super().__init__(master)
        self.image, self.on_select, self.n = image, on_select, 0
        self.title("Select area(s) to OCR  -  drag a box, Esc or Done to finish")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.k = min(2.0, 0.9 * sw / image.width)            # scale: fit the width, enlarge small images
        w, h = max(1, int(image.width * self.k)), max(1, int(image.height * self.k))
        self.photo = ImageTk.PhotoImage(image.resize((w, h), Image.LANCZOS))

        bar = tk.Frame(self)
        bar.pack(fill="x")
        tk.Label(bar, text="Drag a box around the text you want. Each box becomes a new image. Mouse wheel scrolls.",
                 anchor="w").pack(side="left", padx=8, pady=4)
        tk.Button(bar, text="Done", width=8, command=self.destroy).pack(side="right", padx=8, pady=4)
        body = tk.Frame(self)
        body.pack(fill="both", expand=True)
        self.cv = tk.Canvas(body, width=min(w, int(0.9 * sw)), height=min(h, int(0.72 * sh)), bg="#222222",
                            scrollregion=(0, 0, w, h), cursor="cross", highlightthickness=0)
        vs = tk.Scrollbar(body, orient="vertical", command=self.cv.yview)
        hs = tk.Scrollbar(body, orient="horizontal", command=self.cv.xview)
        self.cv.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.cv.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self.cv.create_image(0, 0, image=self.photo, anchor="nw")

        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        self.cv.bind("<MouseWheel>", lambda e: self.cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.cv.bind("<Button-4>", lambda e: self.cv.yview_scroll(-1, "units"))
        self.cv.bind("<Button-5>", lambda e: self.cv.yview_scroll(1, "units"))
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(master)
        self.after(150, self._grab)
        self._start, self._rect = None, None

    def _grab(self):
        """Make the window modal (ignored if the window is not visible yet)."""
        try:
            self.grab_set()
            self.focus_set()
        except tk.TclError:
            pass

    def _press(self, e):
        self._start = (self.cv.canvasx(e.x), self.cv.canvasy(e.y))
        self._rect = self.cv.create_rectangle(*self._start, *self._start, outline="#00aaff", width=2)

    def _drag(self, e):
        if self._rect is not None:
            self.cv.coords(self._rect, *self._start, self.cv.canvasx(e.x), self.cv.canvasy(e.y))

    def _release(self, e):
        if self._rect is None:
            return
        x0, x1 = sorted((self._start[0], self.cv.canvasx(e.x)))
        y0, y1 = sorted((self._start[1], self.cv.canvasy(e.y)))
        if x1 - x0 < 8 or y1 - y0 < 8:                       # an accidental click, not a box
            self.cv.delete(self._rect)
            self._rect = None
            return
        self.n += 1
        self.cv.itemconfigure(self._rect, outline="#22c55e")
        self.cv.create_text(x0 + 6, y0 + 4, text=str(self.n), fill="#22c55e", anchor="nw", font=("Segoe UI", 14, "bold"))
        self._rect = None
        k = self.k                                           # back to original-image pixels
        crop = self.image.crop((int(x0 / k), int(y0 / k), int(x1 / k), int(y1 / k)))
        self.on_select(crop, self.n)
