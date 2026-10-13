import unittest
from types import SimpleNamespace

from app.batch_runtime import batch_plan
from app import local_agents


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

    def test_local_agents_are_local_roles(self):
        names = local_agents.names()
        self.assertIn("OCR Structure", names)
        self.assertIn("Vocabulary", names)
        self.assertIn("Study Tutor", names)
        self.assertTrue(all(row["name"] in names for row in local_agents.describe()))


if __name__ == "__main__":
    unittest.main()
