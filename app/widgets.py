"""
widgets.py - small reusable widgets.

FlowFrame lays its children out from left to right and WRAPS to a new row when the panel is too
narrow. The toolbars of the editor and the buttons of the result cards use it, so nothing is ever
cut off on a small screen or when the user drags a panel divider.
"""
import customtkinter as ctk


class FlowFrame(ctk.CTkFrame):
    """A frame whose children flow like text: as many per row as fit, then the next row.

    Children are positioned with place() at exact coordinates (a grid would force all rows to share
    column widths and leave uneven gaps); the frame's height is set to the rows it needs.
    """

    def __init__(self, master, pad=2, **kw):
        kw.setdefault("height", 32)
        super().__init__(master, fg_color="transparent", **kw)
        self.items, self.pad, self._width = [], pad, -1
        self.bind("<Configure>", self._on_configure)

    def add(self, widget):
        """Register a child (it must have been created with this frame as its master)."""
        self.items.append(widget)
        self.after_idle(self.reflow)
        return widget

    def _on_configure(self, event):
        if event.width != self._width:                     # only when the available width really changed
            self._width = event.width
            self.reflow()

    def reflow(self):
        """Place the children in rows that fit the current width and size the frame to match."""
        width = self.winfo_width()
        if width < 60:
            width = 100000                                # not laid out yet: one row, a Configure event follows
        x = y = row_h = 0
        for w in self.items:
            need, h = w.winfo_reqwidth() + 2 * self.pad, w.winfo_reqheight() + 2 * self.pad
            if x and x + need > width:                    # does not fit: start a new row
                x, y, row_h = 0, y + row_h, 0
            w.place(x=x + self.pad, y=y + self.pad)
            x, row_h = x + need, max(row_h, h)
        self.configure(height=max(1, y + row_h))
