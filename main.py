"""
main.py - entry point of Charlie MJ OCR & Language Studio.

Run from source:   python main.py
Built by PyInstaller into CharlieMJ-OCR.exe (see build.bat / .github/workflows/build.yml).
All the real code lives in the `app/` package (see app/__init__.py).
"""
import ctypes

# Ask Windows for true pixel sizes so screenshot coordinates match the screen on
# high-DPI displays. Must happen BEFORE any window is created. Ignored elsewhere.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

from app.ui import App  # noqa: E402  (imported after the DPI call on purpose)


def main():
    """Create the main window and start the Tk event loop."""
    App().mainloop()


if __name__ == "__main__":
    main()
