import unittest
from pathlib import Path


class PythonSyntaxTests(unittest.TestCase):
    def test_application_modules_compile(self):
        root = Path(__file__).resolve().parents[1]
        targets = [root / "main.py", *sorted((root / "app").glob("*.py"))]
        for path in targets:
            with self.subTest(path=path.relative_to(root)):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


if __name__ == "__main__":
    unittest.main()
