"""Analytics tests: numbers must come from real rows, move when data changes, and respect scope."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import analytics, db, pipeline  # noqa: E402
from backend.bootstrap import bootstrap  # noqa: E402
from backend.demo_seed import seed_demo_activity  # noqa: E402


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_PROVIDER"] = "mock"
        os.environ.pop("SEED_DEMO_DATA", None)
        self.conn = db.connect(":memory:")
        bootstrap(self.conn)
        self.admin = dict(db.get_user_by_username(self.conn, "admin"))

    def test_empty_workspace_is_all_zero_not_an_error(self):
        snap = analytics.snapshot(self.conn, None, 7)
        self.assertEqual(snap["current"]["total"], 0)
        self.assertEqual(len(snap["daily"]), 7)
        self.assertEqual(sum(d["total"] for d in snap["daily"]), 0)
        self.assertEqual(snap["latency"]["p95"], 0)

    def test_new_question_moves_the_numbers(self):
        before = analytics.snapshot(self.conn, None, 7)
        pipeline.ask(self.conn, self.admin, "Can a learner get a refund within 7 days?", "mock")
        after = analytics.snapshot(self.conn, None, 7)
        self.assertEqual(after["current"]["total"], before["current"]["total"] + 1)
        self.assertNotEqual(before["fingerprint"], after["fingerprint"])
        self.assertEqual(after["daily"][-1]["total"], 1)  # today is the last bucket
        self.assertEqual(after["live"][0]["topic"], "refund")

    def test_daily_series_matches_headline_total(self):
        seed_demo_activity(self.conn, days=20)
        snap = analytics.snapshot(self.conn, None, 14)
        self.assertEqual(sum(d["total"] for d in snap["daily"]), snap["current"]["total"])
        self.assertEqual(sum(t["count"] for t in snap["topics"]), snap["current"]["total"])
        self.assertEqual(sum(sum(row) for row in snap["heatmap"]), snap["current"]["total"])

    def test_counsellor_scope_only_sees_own_rows(self):
        seed_demo_activity(self.conn, days=10)
        asha = db.get_user_by_username(self.conn, "demo.asha")["id"]
        mine = analytics.snapshot(self.conn, asha, 30)
        everyone = analytics.snapshot(self.conn, None, 30)
        self.assertLess(mine["current"]["total"], everyone["current"]["total"])
        self.assertEqual(mine["people"], [])  # per-person table is workspace-only

    def test_seed_is_idempotent_and_synthetic(self):
        first = seed_demo_activity(self.conn, days=5)
        self.assertGreater(first, 0)
        self.assertEqual(seed_demo_activity(self.conn, days=5), 0)


if __name__ == "__main__":
    unittest.main()
