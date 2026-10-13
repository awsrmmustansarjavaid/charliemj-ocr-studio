import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import local_agents
from app.batch_runtime import batch_plan, _run_ocr_unified


class BatchRuntimeTests(unittest.TestCase):
    def test_batch_plan_includes_already_done_images(self):
        items = [
            SimpleNamespace(status="done"),
            SimpleNamespace(status="waiting"),
            SimpleNamespace(status="done"),
        ]
        plan = batch_plan(items, "Smart")
        self.assertEqual(len(plan), 3)
        self.assertTrue(all(mode == "Smart" for _, mode in plan))

    def test_card_ocr_uses_same_job_entry_point_as_batch(self):
        calls = []

        def fake_start(app, items, mode):
            calls.append((items, mode))
            return True

        app = object()
        item = {"name": "image-2.jpg"}
        with patch("app.batch_runtime._start_jobs", fake_start):
            self.assertTrue(_run_ocr_unified(app, item, "Smart"))
        self.assertEqual(calls, [([item], "Smart")])

    def test_local_agents_are_local_roles(self):
        names = local_agents.names()
        self.assertIn("OCR Structure", names)
        self.assertIn("Vocabulary", names)
        self.assertIn("Study Tutor", names)
        self.assertTrue(all(row["name"] in names for row in local_agents.describe()))

    def test_local_agent_status_accepts_explicit_url(self):
        expected = (True, ["gemma3:4b"], "ok")
        with patch("app.local_agents.local_ai.status", return_value=expected) as status:
            self.assertEqual(local_agents.status("http://localhost:11434"), expected)
            status.assert_called_once_with("http://localhost:11434")


if __name__ == "__main__":
    unittest.main()
