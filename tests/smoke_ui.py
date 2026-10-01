"""
smoke_ui.py - headless end-to-end check of the real window (needs a display, e.g. xvfb).

Run on Linux:   xvfb-run -a python tests/smoke_ui.py <image1> [<image2> ...]
It adds the given images, runs Smart OCR on all of them, then exercises numbering,
reordering, swap, delete/undo, combine, CSV export and the local-AI buttons
(using a tiny fake Ollama server, so no model is needed).
"""
import csv, json, os, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PIL import Image
from app import ui, local_ai
from app.config import cfg


class FakeOllama(BaseHTTPRequestHandler):
    """Minimal stand-in for Ollama's /api/tags and /api/generate."""
    def log_message(self, *a): pass
    def _send(self, obj):
        b = json.dumps(obj).encode(); self.send_response(200)
        self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._send({"models": [{"name": "gemma3:4b"}]})
    def do_POST(self):
        n = int(self.headers["Content-Length"]); body = json.loads(self.rfile.read(n))
        self._send({"response": f"FAKE-AI({'image' if 'images' in body else 'text'})"})


def pump(app, cond, timeout=120):
    """Run the Tk event loop until cond() is true (background threads post back via after())."""
    end = time.time() + timeout
    while time.time() < end and not cond():
        app.update(); time.sleep(0.05)
    assert cond(), "timeout waiting for background work"


def main(paths):
    srv = HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    cfg["ollama_url"] = f"http://127.0.0.1:{srv.server_port}"
    app = ui.App(); app.update()
    for p in paths:
        assert app.open_path(p)
    n = len(app.items); print("queued:", n)
    app.process_all()
    pump(app, lambda: all(it["status"] == "done" for it in app.items))
    pump(app, lambda: all(it["tb"] is not None for it in app.items))
    app.update()
    for i, it in enumerate(app.items, 1):
        print(f"--- Image {i} ({it['name']}) kind={it['res'].kind if it['res'] else 'raw'}")
    # numbering + separators
    comb = app.combined_text()
    assert comb.count("## Image ") == n and comb.count("\n---\n") == n - 1, "numbering/separators"
    # reorder: move image 1 down -> numbering follows position
    first = app.items[0]["name"]; app.move(0, 1); app.update()
    assert app.items[1]["name"] == first and f"## Image 2\n*{first}*" in app.combined_text()
    # swap columns on a bilingual table
    it = next((x for x in app.items if x["res"] and x["res"].kind == "bilingual"), None)
    if it:
        before = it["md"]; app.swap(it); app.update(); assert it["md"] != before; app.swap(it); app.update()
    # delete + undo
    gone = app.items[0]["name"]; app.remove_items([app.items[0]]); app.update()
    assert len(app.items) == n - 1 and gone not in app.combined_text()
    app.undo_remove(); app.update(); assert len(app.items) == n
    # combine tab
    app.combine_all(); app.update(); assert "## Image 1" in app.combined.get("1.0", "end")
    # CSV export (monkeypatch the save dialog)
    out = os.path.join(tempfile.mkdtemp(), "t.csv")
    ui.filedialog.asksaveasfilename = lambda **k: out
    app.export("csv"); rows = list(csv.reader(open(out, encoding="utf-8-sig")))
    print("csv rows:", len(rows) - 1, rows[:3])
    # local AI: status, text action, vision OCR
    ok, models, msg = local_ai.status(cfg["ollama_url"]); assert ok and models == ["gemma3:4b"], msg
    tb = app.items[0]["tb"]; app.set_active(tb); app.ai_action("Translate"); pump(app, lambda: "FAKE-AI(text)" in tb.get("1.0", "end"))
    app.current = 0; app.ai_ocr_current(); pump(app, lambda: "FAKE-AI(image)" in app.items[0]["md"])
    # privacy guard: non-local addresses must be refused
    ok, _, msg = local_ai.status("http://example.com:11434")
    assert ok is False and "local" in msg.lower(), msg
    try:
        local_ai.generate("http://example.com:11434", "m", "hi"); raise AssertionError("guard failed")
    except RuntimeError:
        pass
    app.refresh_results(); app.update(); app.geometry("1400x800"); app.update()
    app.tabs.set("Results")
    for _ in range(10): app.update(); time.sleep(0.1)       # let the tab redraw
    if os.environ.get("SHOT"):                       # optional screenshot of the window
        from PIL import ImageGrab; ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).save(os.environ["SHOT"])
    print("SMOKE TEST PASSED"); app.destroy()


if __name__ == "__main__":
    main(sys.argv[1:])
