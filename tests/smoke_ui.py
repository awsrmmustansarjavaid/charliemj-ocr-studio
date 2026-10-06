"""
End-to-end smoke test of the real window (needs a display; on Linux use xvfb-run).

    xvfb-run -a python tests/smoke_ui.py

It starts a FAKE local-AI server, then drives the app like a user: opens images, runs the
three OCR modes, selects an area, reorders, swaps, edits, exports and checks every result.
Set SHOT=/path/file.png to also save a screenshot of the window.
"""
import http.server
import json
import os
import sys
import tempfile
import threading
import time
import traceback
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
os.environ.setdefault("TESTING", "1")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from make_poster import font, make_poster  # noqa: E402


class FakeOllama(http.server.BaseHTTPRequestHandler):
    """Pretends to be Ollama: lists one model and answers prompts with canned Markdown."""
    def log_message(self, *a):
        pass

    def _send(self, obj):
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send({"models": [{"name": "gemma3:4b"}]})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        p = body["prompt"]
        if "EXACTLY this structure" in p:       # AI Smart
            self._send({"response": "# Skin Features\n## Face\n### Marks\n- **gamze** — dimple\n- **ben** — mole"})
        else:
            self._send({"response": "FAKE-ANSWER"})


def table_image(path):
    im = Image.new("RGB", (1000, 560), "white")
    d = ImageDraw.Draw(im)
    d.text((60, 30), "Daily Greetings", font=font(True, 44), fill="black")
    for i, (a, b) in enumerate([("Merhaba", "Hello"), ("Günaydın", "Good morning"), ("Nasılsın?", "How are you?"), ("Görüşürüz", "See you")]):
        d.text((80, 130 + i * 85), a, font=font(False, 34), fill="black")
        d.text((560, 130 + i * 85), b, font=font(False, 34), fill="black")
    im.save(path)


def main():
    srv = http.server.HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp()
    poster, table = os.path.join(tmp, "poster.png"), os.path.join(tmp, "table.png")
    make_poster(poster)
    table_image(table)

    from tkinter import messagebox
    messagebox.askyesno = lambda *a, **k: True               # auto-confirm dialogs
    messagebox.showwarning = lambda *a, **k: None
    from app import richtext as rt
    from app.config import cfg
    from app.selector import AreaSelector
    from app.ui import App
    cfg.update(ollama_url=f"http://127.0.0.1:{srv.server_port}", model="gemma3:4b", lang="Turkish", native="English")

    app = App()
    app.update()

    def wait(cond, what, timeout=240):
        end = time.time() + timeout
        while time.time() < end:
            app.update()
            if cond():
                return
            time.sleep(0.03)
        raise AssertionError("timeout waiting for " + what)

    def ed_text():
        return app.editor.t.get("1.0", "end-1c")

    def blocks():
        return app.editor.get_blocks()

    # ---- 1. queue + Smart mode (Process All)
    app.mode.set("Smart")
    app.open_path(poster)
    app.open_path(table)
    app.refresh_all()
    assert len(app.items) == 2
    app.process_all()
    wait(lambda: all(i["status"] == "done" for i in app.items) and "Image 2" in ed_text(), "Smart process")
    poster_item = app.items[0]
    assert poster_item["res"].kind == "bilingual" and len(poster_item["res"].rows) >= 11, poster_item["res"].rows
    assert "TURKISH!... more" not in poster_item["md"].split("Other text")[0]
    print("smart rows:", len(poster_item["res"].rows), "| table title:", app.items[1]["res"].title)

    # ---- 2. editor was filled automatically: Image N title, vocabulary heading, bullets
    st = [(b.style, b.text) for b in blocks()]
    print("editor starts:", st[:3])
    assert st[0] == ("title", "Image 1")
    assert any(s == "h1" and t == "Daily Greetings" for s, t in st), "main title missing"
    assert any(s == "h2" and t == "Vocabulary" for s, t in st)
    assert sum(1 for b in blocks() if b.is_bullet) >= 16
    assert any(t.startswith("• gamze — dimple") for s, t in st)
    assert any(b.hr for b in blocks()), "separator missing"

    # ---- 3. Raw mode = every word
    app.run_ocr(poster_item, "Raw")
    wait(lambda: poster_item["kind"] == "raw" and poster_item["status"] == "done", "raw")
    for w in ("dimple", "çil", "freckle", "güzellik", "cellulite"):
        assert w in poster_item["md"].lower(), w
    assert any(b.style == "h2" and b.text == "Raw text" for b in blocks())

    # ---- 4. AI Smart mode (fake local AI)
    app.run_ocr(poster_item, "AI Smart")
    wait(lambda: poster_item["kind"] == "ai", "ai smart")
    styles = [b.style for b in blocks()]
    assert "h1" in styles and "h2" in styles and "h3" in styles, styles
    assert any(t == "• gamze — dimple" for _, t in [(b.style, b.text) for b in blocks()])

    # ---- 5. Select Area: the result is ADDED to the same image (no new "Image N", no batch slot used)
    app.run_ocr(poster_item, "Smart")
    wait(lambda: poster_item["status"] == "done", "smart again")
    app.mode.set("Raw")
    app.show(0)
    crop = poster_item["img"].crop((0, 300, 1080, 620))
    before = len(app.items)
    assert app.add_area(poster_item, crop, 1) is True
    assert len(app.items) == before and len(poster_item["areas"]) == 1
    area = poster_item["areas"][0]
    wait(lambda: area["status"] == "done", "area OCR")
    assert "gamze" in area["md"].lower()
    texts = [b.text for b in blocks()]
    assert "Area 1" in texts and texts.index("Area 1") > texts.index("Image 1"), texts[:12]
    assert "Area 1" in app.combined_text() or "gamze" in app.combined_text().lower()
    # the "new image" target still works (and honours numbering)
    assert app.add_area(poster_item, crop, 2, "new") and len(app.items) == before + 1 and "area 2" in app.items[1]["name"]
    wait(lambda: app.items[1]["status"] == "done", "new-image area OCR")
    assert any(b.style == "title" and b.text == "Image 2" for b in blocks())
    app.remove_area(area)
    assert not poster_item["areas"]

    # ---- 6. reorder -> numbering follows
    app.move(0, 1)
    assert app.items[1]["name"] == "poster.png"
    assert [b.text for b in blocks() if b.style == "title"] == ["Image 1", "Image 2", "Image 3"]

    # ---- 7. Swap
    app.mode.set("Smart")
    t_item = next(i for i in app.items if i["name"] == "table.png")
    first = t_item["res"].rows[0]
    app.swap(t_item)
    assert layout_first(t_item) == (first[1], first[0]), layout_first(t_item)
    app.swap(t_item)

    # ---- 8. editing: formatting, dirty flag protects the user's text, Restore
    ed = app.editor
    ed.t.tag_add("sel", "1.0", "1.7")
    ed.toggle("b")
    ed.t.tag_remove("sel", "1.0", "end")
    ed.t.insert("end", "\nMy own note")
    app.update()
    ed._modified()
    assert ed.dirty
    before = ed_text()
    app.remove_items([app.items[1]])
    assert ed_text() == before, "auto update must not overwrite user edits"
    app.sync_editor(True)
    assert "My own note" not in ed_text() and not ed.dirty
    ed.restore()
    assert "My own note" in ed_text()
    app.sync_editor(True)

    # ---- 9. AI action on the editor (fake)
    ed.t.tag_add("sel", "1.0", "3.0")
    app.ai_action("Translate")
    wait(lambda: "FAKE-ANSWER" in ed_text(), "AI action")

    # ---- 10. exports
    app.sync_editor(True)
    for kind in ("md", "txt", "html", "docx", "csv"):
        ed.write(os.path.join(tmp, "out." + kind), kind)
    csv_rows = open(os.path.join(tmp, "out.csv"), encoding="utf-8-sig").read().splitlines()
    assert csv_rows[0] == "Image,Original,Translation" and len(csv_rows) >= 5, csv_rows[:3]   # header + the 4 table rows
    import zipfile
    assert zipfile.ZipFile(os.path.join(tmp, "out.docx")).testzip() is None
    print("csv sample:", csv_rows[1:3])

    # ---- 11. selection window: zoom / fit / select / crop / rotate (simulated mouse)
    got, replaced = [], []
    sel = AreaSelector(app, poster_item["img"], lambda c, n, t: got.append((c.size, n, t)), replaced.append)
    app.update()
    sel.fit()
    sel.update()
    k_fit = sel.k
    assert 0.03 < k_fit <= 1.0
    sel.zoom(2.0)
    assert sel.k > k_fit
    sel.fit_width()
    sel.actual()
    assert sel.k == 1.0
    sel.fit()
    sel.update()
    ev = types.SimpleNamespace
    sel._press(ev(x=50, y=60))
    sel._drag(ev(x=300, y=200))
    sel._release(ev(x=300, y=200))
    assert got and got[0][1] == 1 and got[0][2] == "same" and got[0][0][0] > 100, got
    sel.target.set("crop")
    w0 = sel.src.width
    sel._press(ev(x=50, y=60))
    sel._release(ev(x=300, y=200))
    assert replaced and replaced[-1].width < w0
    h0 = sel.src.height
    sel.rotate(90)
    assert sel.src.width == h0
    sel.undo_edit()
    sel.undo_edit()
    assert sel.src.width == w0
    sel.destroy()

    # ---- 12. focus mode, settings, AI status
    app.toggle_focus()
    app.update()
    app.toggle_focus()
    app.update()
    wait(lambda: "gemma3:4b" in app.ai_lbl.cget("text"), "AI status")

    if os.environ.get("SHOT"):
        app.show(0)
        app.update()
        time.sleep(0.5)
        app.update()
        ImageGrab_grab(app).save(os.environ["SHOT"])
    app.destroy()
    print("SMOKE TEST PASSED")


def layout_first(item):
    from app import layout
    return layout.extract_pairs(item["md"])[0]


def ImageGrab_grab(app):
    from PIL import ImageGrab
    x, y, w, h = app.winfo_rootx(), app.winfo_rooty(), app.winfo_width(), app.winfo_height()
    return ImageGrab.grab(bbox=(x, y, x + w, y + h), xdisplay=os.environ.get("DISPLAY"))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
