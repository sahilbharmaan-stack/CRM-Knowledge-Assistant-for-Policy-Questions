"""Regression tests for role-based login and upload error handling."""
import asyncio
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.datastructures import UploadFile  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from backend import auth, db  # noqa: E402
from backend.documents import MAX_BYTES  # noqa: E402
from backend.main import LoginIn, login, upload_policy  # noqa: E402


class ApiAccessAndUploadTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.migrate(self.conn)
        self.admin_id = db.create_user(self.conn, "admin_test", "not-a-real-hash", "administrator")
        self.admin = dict(db.get_user(self.conn, self.admin_id))

    def tearDown(self):
        self.conn.close()

    def test_login_detects_role_without_panel_selection(self):
        for username, role in (("login_admin", "administrator"), ("login_customer", "counsellor")):
            user_id = db.create_user(self.conn, username, auth.hash_password("secure-test-password"), role)
            session = login(LoginIn(username=username, password="secure-test-password"), self.conn)
            self.assertEqual(session["id"], user_id)
            self.assertEqual(session["role"], role)

    def test_invalid_uploads_return_client_errors_not_server_errors(self):
        invalid_files = (("broken.pdf", b"not a pdf"), ("broken.docx", b"not a docx"))
        for filename, contents in invalid_files:
            with self.subTest(filename=filename):
                upload = UploadFile(filename=filename, file=io.BytesIO(contents))
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(upload_policy(
                        file=upload,
                        doc_code="CL-TEST-001",
                        title="Test policy",
                        version="1.0",
                        user=self.admin,
                        conn=self.conn,
                    ))
                self.assertEqual(raised.exception.status_code, 400)

    def test_valid_text_upload_creates_draft(self):
        upload = UploadFile(filename="policy.txt", file=io.BytesIO(b"Policy body for the upload test."))
        result = asyncio.run(upload_policy(
            file=upload,
            doc_code="CL-TEST-003",
            title="Upload test policy",
            version="1.0",
            user=self.admin,
            conn=self.conn,
        ))

        self.assertEqual(result["status"], "draft")
        self.assertEqual(result["sections"], 1)
        document = db.find_document(self.conn, "CL-TEST-003", "1.0")
        self.assertEqual(document["status"], "draft")

    def test_large_upload_is_rejected_without_reading_the_whole_file(self):
        upload = UploadFile(filename="large.txt", file=io.BytesIO(b"x" * (MAX_BYTES + 1)))
        with self.assertRaises(HTTPException) as raised:
            asyncio.run(upload_policy(
                file=upload,
                doc_code="CL-TEST-002",
                title="Large policy",
                version="1.0",
                user=self.admin,
                conn=self.conn,
            ))
        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
