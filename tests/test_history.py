"""History API compatibility tests for databases created by older releases."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db  # noqa: E402
from backend.main import history as history_endpoint  # noqa: E402


class HistoryMigrationTests(unittest.TestCase):
    def test_history_works_after_migrating_legacy_answers(self):
        conn = db.connect(":memory:")
        try:
            db.init_schema(conn)
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES ('olduser', 'x', 'counsellor')"
            )
            conn.execute(
                "INSERT INTO staff_queries (user_id, query_text, status) "
                "VALUES (1, 'legacy history query', 'answered')"
            )
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript("""
                CREATE TABLE answers_legacy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_id INTEGER NOT NULL REFERENCES staff_queries(id) ON DELETE CASCADE,
                    answer_text TEXT,
                    citations_json TEXT NOT NULL DEFAULT '[]',
                    abstained INTEGER NOT NULL DEFAULT 0,
                    provider TEXT,
                    model TEXT,
                    latency_ms INTEGER,
                    prompt_version TEXT,
                    feedback TEXT,
                    feedback_note TEXT,
                    reviewed_by INTEGER REFERENCES users(id),
                    reviewed_at TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                INSERT INTO answers_legacy (query_id, answer_text) VALUES (1, 'legacy answer');
                DROP TABLE answers;
                ALTER TABLE answers_legacy RENAME TO answers;
            """)

            db.init_schema(conn)
            db.migrate(conn)
            user = dict(db.get_user_by_username(conn, "olduser"))
            rows = history_endpoint(user=user, conn=conn)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["answer_text"], "legacy answer")
            self.assertEqual(rows[0]["review_status"], "pending_review")
            self.assertEqual(rows[0]["citations"], [])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
