import threading
import time
import unittest

from app.job_manager import OCRJobManager


class OCRJobManagerTests(unittest.TestCase):
    def test_processes_every_item_even_when_previous_status_is_done(self):
        items = [
            {"name": "one.png", "status": "done"},
            {"name": "two.png", "status": "waiting"},
            {"name": "three.png", "status": "done"},
        ]
        finished = threading.Event()
        seen = []
        states = []

        manager = OCRJobManager()
        started = manager.start(
            items,
            "Smart",
            lambda item, mode: (seen.append((item["name"], mode)) or item["name"]),
            on_start=lambda job: states.append((job.number, "start")),
            on_result=lambda job: states.append((job.number, "done")),
            on_error=lambda job: states.append((job.number, "error")),
            on_finish=lambda jobs: finished.set(),
        )
        self.assertTrue(started)
        self.assertTrue(finished.wait(5))
        self.assertEqual([name for name, _ in seen], ["one.png", "two.png", "three.png"])
        self.assertEqual([mode for _, mode in seen], ["Smart", "Smart", "Smart"])
        self.assertEqual([job.status for job in manager.jobs], ["done", "done", "done"])
        self.assertEqual(states, [(1, "start"), (1, "done"), (2, "start"), (2, "done"), (3, "start"), (3, "done")])

    def test_one_failure_does_not_stop_later_images(self):
        items = [{"name": "bad.png"}, {"name": "good.png"}]
        finished = threading.Event()

        def worker(item, mode):
            if item["name"] == "bad.png":
                raise RuntimeError("synthetic OCR failure")
            return "ok"

        manager = OCRJobManager()
        manager.start(items, "Raw", worker, on_finish=lambda jobs: finished.set())
        self.assertTrue(finished.wait(5))
        self.assertEqual(manager.jobs[0].status, "error")
        self.assertEqual(manager.jobs[0].error, "synthetic OCR failure")
        self.assertEqual(manager.jobs[1].status, "done")


if __name__ == "__main__":
    unittest.main()
