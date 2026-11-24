"""Regression coverage for partially upgraded account and policy schemas."""
from concurrent.futures import ThreadPoolExecutor
import os
import tempfile
import unittest
from unittest.mock import patch

from backend import db
from backend.main import get_conn
from backend.main import policies as policies_endpoint
from backend.main import shares as shares_endpoint
from backend.main import users as users_endpoint


class SharingMigrationTests(unittest.TestCase):
    def test_customer_policy_filters_apply_without_exposing_unapproved_documents(self):
        conn = db.connect(":memory:")
        try:
            db.init_schema(conn)
            db.migrate(conn)
            customer_id = db.create_user(conn, "policy_customer", "test-hash", "counsellor")
            db.insert_document(conn, "CL-OPEN-001", "Approved policy", "1.0", None, "approved")
            db.insert_document(conn, "CL-DRAFT-001", "Draft policy", "1.0", None, "draft")
            customer = dict(db.get_user(conn, customer_id))

            approved = policies_endpoint(user=customer, status="approved", conn=conn)
            draft = policies_endpoint(user=customer, status="draft", conn=conn)

            self.assertEqual([document["doc_code"] for document in approved], ["CL-OPEN-001"])
            self.assertEqual(draft, [])
        finally:
            conn.close()

    def test_partial_legacy_schema_supports_admin_sharing_queries(self):
        conn = db.connect(":memory:")
        try:
            conn.executescript("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('administrator', 'counsellor')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE TABLE policy_documents (
                    id INTEGER PRIMARY KEY,
                    doc_code TEXT NOT NULL,
                    title TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('draft', 'pending', 'approved', 'rejected')),
                    source_path TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
            """)
            db.init_schema(conn)
            conn.execute(
                "INSERT INTO users (username, password_hash, role) "
                "VALUES ('admin', 'test-hash', 'administrator')"
            )
            conn.execute(
                "INSERT INTO policy_documents (doc_code, title, version, status) "
                "VALUES ('CL-TEST-001', 'Test policy', '1.0', 'approved')"
            )

            db.migrate(conn)
            db.migrate(conn)

            admin = dict(db.get_user_by_username(conn, "admin"))
            users = users_endpoint(_user=admin, conn=conn)
            policies = policies_endpoint(user=admin, status="approved", conn=conn)
            shares = shares_endpoint(_user=admin, conn=conn)
            self.assertEqual(users[0]["display_name"], None)
            self.assertEqual(users[0]["active"], 1)
            self.assertEqual(policies[0]["review_note"], None)
            self.assertEqual(policies[0]["status"], "approved")
            self.assertEqual(shares, [])
        finally:
            conn.close()

    def test_concurrent_connections_serialize_database_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = os.path.join(directory, "crm.db")

            def config_value(name, default=None):
                return database_path if name == "DB_PATH" else default

            def list_shares(_):
                dependency = get_conn()
                conn = next(dependency)
                try:
                    admin = dict(db.get_user_by_username(conn, "admin"))
                    return shares_endpoint(_user=admin, conn=conn)
                finally:
                    dependency.close()

            with patch("backend.config.get", side_effect=config_value):
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(list_shares, range(16)))

            self.assertEqual(results, [[]] * 16)


if __name__ == "__main__":
    unittest.main()
