from types import SimpleNamespace

from app.complete_ocr import _coverage_lines, install


def test_coverage_lines_preserves_unrepresented_ocr_text():
    res = SimpleNamespace(
        title="Vocabulary",
        subtitle="English",
        rows=[("hello", "merhaba")],
        other=[],
    )
    raw = "Vocabulary\nhello\nmerhaba\nsecond word\nthird word"
    assert _coverage_lines(res, raw) == ["second word", "third word"]


def test_full_screenshot_does_not_use_reference_pair_count():
    calls = []
    app = SimpleNamespace()
    app._complete_ocr_installed = False
    app.codes = lambda: ("tur+eng", "tur", "eng")

    def smart(img, min_pairs=3):
        calls.append(min_pairs)
        return SimpleNamespace(
            raw="word 1\nword 2",
            title="",
            subtitle="",
            rows=[(f"word {i}", f"meaning {i}") for i in range(30)],
            other=[],
        )

    app.smart = smart
    install(app)
    app.smart("image", 30)
    assert calls == [1]


def test_full_raw_pass_can_add_more_lines_to_smart_result(monkeypatch):
    app = SimpleNamespace()
    app._complete_ocr_installed = False
    app.codes = lambda: ("tur+eng", "tur", "eng")
    app.smart = lambda img, min_pairs=3: SimpleNamespace(
        raw="one\ntwo",
        title="",
        subtitle="",
        rows=[("one", "bir")],
        other=[],
    )
    monkeypatch.setattr("app.complete_ocr.ocr_engine.read_raw", lambda img, code: "one\ntwo\nthree\nfour")
    install(app)
    result = app.smart("image", 3)
    assert result.raw.splitlines() == ["one", "two", "three", "four"]
    assert result.other[-2:] == ["three", "four"]
