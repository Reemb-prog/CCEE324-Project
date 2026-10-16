"""Stage 06: final deliverable existence, not a substitute for report review."""
import unittest
from pathlib import Path

class TestDeliverables(unittest.TestCase):
    def test_reports_are_nonempty(self):
        root=Path(__file__).resolve().parents[1]
        for name in ("docs/FINAL_REPORT.md","docs/RESULTS.md","docs/DEMO_SCRIPT.md","docs/EXPLANATIONS.md","docs/ARCHITECTURE.md","dualcore/demo.py"):
            with self.subTest(name=name):
                p=root/name
                self.assertTrue(p.is_file(),f"Missing: {name}")
                self.assertGreater(len(p.read_text(encoding="utf-8").strip()),180,f"Incomplete: {name}")

    def test_report_mentions_required_concepts(self):
        root=Path(__file__).resolve().parents[1]
        t=(root/"docs/FINAL_REPORT.md").read_text(encoding="utf-8").lower()
        for word in ("pc","alu","register","control","shared","load","store","halt","bonus","test"):
            with self.subTest(word=word):self.assertIn(word,t)
