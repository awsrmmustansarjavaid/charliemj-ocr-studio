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
from app.complete_ocr import install as install_complete_ocr  # noqa: E402
from app.workspace_ui import install as install_study_workspace  # noqa: E402


def main():
    """Create the main window, install additive OCR/study tools and start Tk."""
    app = App()
    install_complete_ocr(app)
    install_study_workspace(app)
    app.mainloop()


if __name__ == "__main__":
    main()
