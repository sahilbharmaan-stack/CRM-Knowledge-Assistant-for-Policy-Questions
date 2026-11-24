"""Data-driven tests from tests/test_questions.json (offline mock provider).
Run: python -m unittest tests.test_questions -v
Q22 is for the live demo with a real LLM and is skipped here."""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db, pipeline  # noqa: E402
from backend.bootstrap import bootstrap  # noqa: E402

CASES = json.loads((Path(__file__).parent / "test_questions.json").read_text(encoding="utf-8"))


class QuestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["LLM_PROVIDER"] = "mock"
        os.environ["SEED_DEMO_USERS"] = "1"
        os.environ.setdefault("DEMO_PASSWORD", "demo-pass-123")
        os.environ.pop("GEMINI_API_KEY", None)
        cls.conn = db.connect(":memory:")
        bootstrap(cls.conn)
        cls.user = dict(db.get_user_by_username(cls.conn, "counsellor1"))

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def run_case(self, case):
        provider = "gemini" if case["type"] == "api_failure" else "mock"
        return pipeline.ask(self.conn, self.user, case["question"], provider)

    def check(self, case):
        r = self.run_case(case)
        t = case["type"]
        if t == "answer":
            self.assertEqual(r["status"], "answered", r)
            top = r["citations"][0]
            self.assertEqual(top["doc_code"], case["expect_doc"])
            self.assertEqual(top["version"], case["expect_version"])
            self.assertIn(case["expect_heading"].lower(), (top["heading"] or "").lower())
        elif t == "abstain":
            self.assertEqual(r["status"], "abstained", r)
            self.assertEqual(r["citations"], [])
        elif t == "old_version":
            self.assertTrue(all(p["version"] != "1.0" for p in r["passages"]))
            self.assertTrue(all(c["version"] == "2.1" for c in r["citations"]))
        elif t == "unsupported_action":
            self.assertEqual(r.get("review_status"), "pending_review")
            n = self.conn.execute("SELECT COUNT(*) c FROM answers WHERE status='approved'").fetchone()["c"]
            self.assertEqual(n, 0)
        elif t == "reject":
            self.assertEqual(r["status"], "rejected")
        elif t == "injection":
            self.assertIn(r["status"], ("answered", "abstained"))
            self.assertEqual(r.get("review_status"), "pending_review")
        elif t == "api_failure":
            self.assertEqual(r["status"], "api_error")
            self.assertTrue(r["passages"])


def _make(case):
    def test(self):
        if case["type"] == "real_llm_only":
            self.skipTest("needs a real LLM (live demo)")
        self.check(case)
    return test


for _c in CASES:
    setattr(QuestionTests, f"test_{_c['id'].lower()}_{_c['type']}", _make(_c))

if __name__ == "__main__":
    unittest.main()
