import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from app.flashcards import Flashcard, due_cards
from app.history import History
from app.project_store import load_project, save_project
from app.study_workspace import StudyWorkspace
from app.vocabulary import extract_pairs, from_records, merge, stats, to_anki


class StudyFeatureTests(unittest.TestCase):
    def test_vocabulary_extracts_and_deduplicates_stably(self):
        text = "- **merhaba** — hello\n- **ev** — house\n- **merhaba** — hello\nignored"
        entries = from_records(extract_pairs(text), "Turkish", "one.png")
        self.assertEqual([(e.source, e.translation) for e in entries], [("merhaba", "hello"), ("ev", "house")])
        self.assertEqual(stats(entries)["total"], 2)
        self.assertEqual(to_anki(entries).splitlines()[0], "merhaba\thello")

    def test_workspace_never_drops_existing_vocabulary(self):
        ws = StudyWorkspace()
        self.assertEqual(ws.ingest_pairs([("a", "A"), ("b", "B")]), 2)
        self.assertEqual(ws.ingest_pairs([("b", "B"), ("c", "C")]), 1)
        self.assertEqual([e.source for e in ws.vocabulary], ["a", "b", "c"])
        self.assertEqual(ws.make_flashcards(), 3)
        self.assertEqual(ws.make_flashcards(), 0)

    def test_flashcard_review_and_due(self):
        card = Flashcard("a", "A")
        card.review(5, date(2026, 1, 1))
        self.assertEqual(card.due, "2026-01-02")
        self.assertEqual(len(due_cards([card], date(2026, 1, 1))), 0)
        self.assertEqual(len(due_cards([card], date(2026, 1, 2))), 1)

    def test_history_undo(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(os.path.join(d, "history.json"))
            h.record("old", "new", "ocr correction")
            self.assertEqual(h.undo("new"), "old")
            self.assertIsNone(h.undo("new"))

    def test_project_manifest_is_portable(self):
        with tempfile.TemporaryDirectory() as d:
            project_dir = os.path.join(d, "Turkish")
            save_project(project_dir, {"name": "Turkish", "language": "Turkish", "items": []})
            loaded = load_project(project_dir)
            self.assertEqual(loaded["name"], "Turkish")
            self.assertEqual(loaded["format_version"], 1)
            self.assertTrue(os.path.exists(os.path.join(project_dir, "project.json")))


if __name__ == "__main__":
    unittest.main()
