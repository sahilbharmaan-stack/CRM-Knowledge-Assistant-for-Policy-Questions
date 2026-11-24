"""SQLite access layer (sqlite3) with CRUD helpers and audit logging."""
import json
import sqlite3

from backend import config

SCHEMA_PATH = config.ROOT / "schema.sql"


def db_path() -> str:
    explicit = config.get("DB_PATH")
    if explicit:
        return explicit
    if config.get("VERCEL"):
        # Vercel's filesystem is read-only except /tmp (ephemeral!)
        return "/tmp/crm_assistant.db"
    return str(config.ROOT / "crm_assistant.db")


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def _table_sql(conn, name: str) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row["sql"] if row else ""


def _columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def migrate(conn: sqlite3.Connection) -> None:
    """Upgrade databases created before roles, account status, policy approval, and answer review."""
    conn.execute("PRAGMA foreign_keys=OFF")
    users_sql = _table_sql(conn, "users")
    if users_sql and "administrator" not in users_sql:
        conn.execute("""
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('administrator', 'policy_manager', 'counsellor', 'reviewer')),
                display_name TEXT,
                active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            INSERT INTO users_new (id, username, password_hash, role, display_name, active, created_at)
            SELECT id, username, password_hash, role, NULL, 1, created_at FROM users
        """)
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_new RENAME TO users")

    user_cols = _columns(conn, "users")
    if "display_name" not in user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if "active" not in user_cols:
        conn.execute(
            "ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1 "
            "CHECK (active IN (0, 1))"
        )

    policy_sql = _table_sql(conn, "policy_documents")
    if policy_sql and "pending" not in policy_sql:
        conn.execute("""
            CREATE TABLE policy_documents_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_code TEXT NOT NULL,
                title TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'archived', 'retired')),
                source_path TEXT,
                review_note TEXT,
                submitted_by INTEGER REFERENCES users(id),
                reviewed_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (doc_code, version)
            )
        """)
        conn.execute("""
            INSERT INTO policy_documents_new
                (id, doc_code, title, version, status, source_path, created_at, updated_at)
            SELECT id, doc_code, title, version, status, source_path, created_at, updated_at
            FROM policy_documents
        """)
        conn.execute("DROP TABLE policy_documents")
        conn.execute("ALTER TABLE policy_documents_new RENAME TO policy_documents")

    policy_cols = _columns(conn, "policy_documents")
    if "review_note" not in policy_cols:
        conn.execute("ALTER TABLE policy_documents ADD COLUMN review_note TEXT")
    if "submitted_by" not in policy_cols:
        conn.execute("ALTER TABLE policy_documents ADD COLUMN submitted_by INTEGER REFERENCES users(id)")
    if "reviewed_by" not in policy_cols:
        conn.execute("ALTER TABLE policy_documents ADD COLUMN reviewed_by INTEGER REFERENCES users(id)")

    answer_cols = _columns(conn, "answers")
    if "status" not in answer_cols:
        conn.execute(
            "ALTER TABLE answers ADD COLUMN status TEXT NOT NULL DEFAULT 'pending_review' "
            "CHECK (status IN ('pending_review', 'approved', 'rejected'))"
        )
    if "review_note" not in answer_cols:
        conn.execute("ALTER TABLE answers ADD COLUMN review_note TEXT")
    if "escalated" not in answer_cols:
        conn.execute("ALTER TABLE answers ADD COLUMN escalated INTEGER NOT NULL DEFAULT 0")
    if "escalation_note" not in answer_cols:
        conn.execute("ALTER TABLE answers ADD COLUMN escalation_note TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_topic ON policy_chunks(topic)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_queries_user ON staff_queries(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_passages_query ON retrieved_passages(query_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_query ON answers(query_id)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS policy_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES policy_documents(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            shared_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(document_id, user_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_policy_shares_user ON policy_shares(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.commit()


def audit(conn, actor: str, action: str, entity: str | None = None,
          entity_id: int | None = None, detail: str | None = None, commit: bool = True) -> None:
    conn.execute(
        "INSERT INTO audit_log (actor, action, entity, entity_id, detail) VALUES (?,?,?,?,?)",
        (actor, action, entity, entity_id, detail),
    )
    if commit:
        conn.commit()


def get_user_by_username(conn, username: str):
    return conn.execute(
        "SELECT * FROM users WHERE lower(username) = lower(?)",
        (username.strip(),),
    ).fetchone()


def get_user(conn, user_id: int):
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def count_users(conn) -> int:
    return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]


def list_users(conn):
    return [dict(r) for r in conn.execute(
        "SELECT id, username, role, display_name, active, created_at FROM users ORDER BY id"
    ).fetchall()]


def create_user(conn, username: str, password_hash: str, role: str, display_name: str | None = None) -> int:
    cur = conn.execute(
        "INSERT INTO users (username, password_hash, role, display_name, active) VALUES (?,?,?,?,1)",
        (username, password_hash, role, display_name),
    )
    conn.commit()
    return cur.lastrowid


def set_password(conn, user_id: int, password_hash: str) -> None:
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, user_id))
    conn.commit()


def update_user(conn, user_id: int, role: str | None = None, active: int | None = None,
                display_name: str | None = None) -> None:
    if role is not None:
        conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    if active is not None:
        conn.execute("UPDATE users SET active=? WHERE id=?", (int(active), user_id))
    if display_name is not None:
        conn.execute("UPDATE users SET display_name=? WHERE id=?", (display_name, user_id))
    conn.commit()


def get_setting(conn, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES (?,?,datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
        (key, value),
    )
    conn.commit()


def upsert_document(conn, doc_code, title, version, source_path, status="approved") -> int:
    row = conn.execute(
        "SELECT id FROM policy_documents WHERE doc_code=? AND version=?", (doc_code, version)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM policy_chunks WHERE document_id=?", (row["id"],))
        conn.execute(
            "UPDATE policy_documents SET title=?, source_path=?, status=?, updated_at=datetime('now') WHERE id=?",
            (title, source_path, status, row["id"]),
        )
        conn.commit()
        return row["id"]
    cur = conn.execute(
        "INSERT INTO policy_documents (doc_code, title, version, status, source_path) VALUES (?,?,?,?,?)",
        (doc_code, title, version, status, source_path),
    )
    conn.commit()
    return cur.lastrowid


def insert_document(conn, doc_code, title, version, source_path, status, submitted_by=None, commit=True) -> int:
    cur = conn.execute(
        "INSERT INTO policy_documents (doc_code, title, version, status, source_path, submitted_by) "
        "VALUES (?,?,?,?,?,?)",
        (doc_code, title, version, status, source_path, submitted_by),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def add_chunk(conn, document_id, chunk_index, heading, text, topic, commit=True) -> int:
    cur = conn.execute(
        "INSERT INTO policy_chunks (document_id, chunk_index, heading, text, topic) VALUES (?,?,?,?,?)",
        (document_id, chunk_index, heading, text, topic),
    )
    if commit:
        conn.commit()
    return cur.lastrowid


def get_document(conn, document_id: int):
    return conn.execute("SELECT * FROM policy_documents WHERE id=?", (document_id,)).fetchone()


def document_chunks(conn, document_id: int):
    return [dict(r) for r in conn.execute(
        "SELECT id, chunk_index, heading, text, topic FROM policy_chunks "
        "WHERE document_id=? ORDER BY chunk_index",
        (document_id,),
    ).fetchall()]


def find_document(conn, doc_code: str, version: str):
    return conn.execute(
        "SELECT * FROM policy_documents WHERE doc_code=? AND version=?", (doc_code, version)
    ).fetchone()


def set_document_status(conn, document_id: int, status: str, reviewer_id: int | None, note: str | None) -> None:
    conn.execute(
        "UPDATE policy_documents SET status=?, reviewed_by=?, review_note=?, updated_at=datetime('now') WHERE id=?",
        (status, reviewer_id, note, document_id),
    )
    conn.commit()


def mark_submitted(conn, document_id: int, user_id: int) -> None:
    conn.execute(
        "UPDATE policy_documents SET status='pending', submitted_by=?, updated_at=datetime('now') WHERE id=?",
        (user_id, document_id),
    )
    conn.commit()


def approved_chunks(conn, topic: str | None = None):
    sql = (
        "SELECT c.id, c.heading, c.text, c.topic, d.doc_code, d.title, d.version "
        "FROM policy_chunks c JOIN policy_documents d ON d.id = c.document_id "
        "WHERE d.status = 'approved'"
    )
    params: tuple = ()
    if topic:
        sql += " AND c.topic = ?"
        params = (topic,)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_documents(conn, status: str | None = None, search: str | None = None, approved_only: bool = False):
    sql = (
        "SELECT d.id, d.doc_code, d.title, d.version, d.status, d.source_path, d.review_note, "
        "d.updated_at, (SELECT COUNT(*) FROM policy_chunks c WHERE c.document_id=d.id) AS chunks "
        "FROM policy_documents d WHERE 1=1"
    )
    params: list = []
    if approved_only:
        sql += " AND d.status='approved'"
    if status:
        sql += " AND d.status=?"
        params.append(status)
    if search:
        sql += " AND (d.doc_code LIKE ? OR d.title LIKE ? OR d.version LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like])
    sql += " ORDER BY d.doc_code, d.version"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def create_query(conn, user_id, query_text, cleaned_text=None, topic=None,
                 confidence=None, status="received") -> int:
    cur = conn.execute(
        "INSERT INTO staff_queries (user_id, query_text, cleaned_text, topic, topic_confidence, status) "
        "VALUES (?,?,?,?,?,?)",
        (user_id, query_text, cleaned_text, topic, confidence, status),
    )
    conn.commit()
    return cur.lastrowid


def set_query_status(conn, query_id: int, status: str) -> None:
    conn.execute("UPDATE staff_queries SET status=? WHERE id=?", (status, query_id))
    conn.commit()


def add_passage(conn, query_id, chunk_id, rank, score) -> None:
    conn.execute(
        "INSERT INTO retrieved_passages (query_id, chunk_id, rank, score) VALUES (?,?,?,?)",
        (query_id, chunk_id, rank, score),
    )
    conn.commit()


def create_answer(conn, query_id, answer_text, citations, abstained, provider=None,
                  model=None, latency_ms=None, prompt_version=None, error=None) -> int:
    cur = conn.execute(
        "INSERT INTO answers (query_id, answer_text, citations_json, abstained, provider, model, "
        "latency_ms, prompt_version, error) VALUES (?,?,?,?,?,?,?,?,?)",
        (query_id, answer_text, json.dumps(citations), int(abstained), provider, model,
         latency_ms, prompt_version, error),
    )
    conn.commit()
    return cur.lastrowid


def get_answer(conn, answer_id: int):
    return conn.execute("SELECT * FROM answers WHERE id=?", (answer_id,)).fetchone()


def get_answer_context(conn, answer_id: int):
    return conn.execute(
        "SELECT a.*, q.user_id, q.query_text FROM answers a "
        "JOIN staff_queries q ON q.id=a.query_id WHERE a.id=?",
        (answer_id,),
    ).fetchone()


def set_feedback(conn, answer_id: int, feedback: str, note: str | None) -> None:
    conn.execute("UPDATE answers SET feedback=?, feedback_note=? WHERE id=?",
                 (feedback, note, answer_id))
    conn.commit()


def review_answer(conn, answer_id: int, reviewer_id: int, status: str, note: str | None = None) -> None:
    conn.execute(
        "UPDATE answers SET status=?, reviewed_by=?, reviewed_at=datetime('now'), review_note=?, escalated=0 "
        "WHERE id=?",
        (status, reviewer_id, note, answer_id),
    )
    conn.commit()


def escalate_answer(conn, answer_id: int, note: str | None) -> None:
    conn.execute(
        "UPDATE answers SET escalated=1, escalation_note=? WHERE id=?",
        (note, answer_id),
    )
    conn.commit()


def history(conn, user_id: int | None = None, limit: int = 50, search: str | None = None,
            query_status: str | None = None):
    sql = (
        "SELECT q.id AS query_id, q.user_id, u.username, q.query_text, q.topic, q.topic_confidence, "
        "q.status AS query_status, q.created_at, a.id AS answer_id, a.answer_text, a.citations_json, "
        "a.abstained, a.provider, a.model, a.latency_ms, a.prompt_version, a.status AS review_status, "
        "a.feedback, a.feedback_note, a.review_note, a.escalated, a.escalation_note "
        "FROM staff_queries q JOIN users u ON u.id=q.user_id "
        "LEFT JOIN answers a ON a.query_id=q.id WHERE 1=1"
    )
    params: list = []
    if user_id is not None:
        sql += " AND q.user_id=?"
        params.append(user_id)
    if search:
        sql += " AND q.query_text LIKE ?"
        params.append(f"%{search}%")
    if query_status:
        sql += " AND q.status=?"
        params.append(query_status)
    sql += " ORDER BY q.id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    for row in rows:
        row["passages"] = passages_for_query(conn, row["query_id"])
    return rows


def passages_for_query(conn, query_id: int):
    return [dict(r) for r in conn.execute(
        "SELECT p.rank, p.score, c.id AS chunk_id, c.heading, d.doc_code, d.version "
        "FROM retrieved_passages p JOIN policy_chunks c ON c.id=p.chunk_id "
        "JOIN policy_documents d ON d.id=c.document_id WHERE p.query_id=? ORDER BY p.rank",
        (query_id,),
    ).fetchall()]


def dashboard_counts(conn, user_id: int | None = None) -> dict:
    where = "WHERE user_id=?" if user_id is not None else ""
    params = (user_id,) if user_id is not None else ()
    questions = conn.execute(f"SELECT COUNT(*) AS c FROM staff_queries {where}", params).fetchone()["c"]
    unanswered = conn.execute(
        f"SELECT COUNT(*) AS c FROM staff_queries {where}{' AND' if where else 'WHERE'} status='abstained'",
        params,
    ).fetchone()["c"]
    answered = conn.execute(
        f"SELECT COUNT(*) AS c FROM staff_queries {where}{' AND' if where else 'WHERE'} status='answered'",
        params,
    ).fetchone()["c"]
    feedback_sql = (
        "SELECT a.feedback, COUNT(*) AS c FROM answers a JOIN staff_queries q ON q.id=a.query_id "
        "WHERE a.feedback IS NOT NULL"
    )
    feedback_params: tuple = ()
    if user_id is not None:
        feedback_sql += " AND q.user_id=?"
        feedback_params = (user_id,)
    feedback_sql += " GROUP BY a.feedback"
    feedback = {row["feedback"]: row["c"] for row in conn.execute(feedback_sql, feedback_params)}
    pending_reviews = conn.execute(
        "SELECT COUNT(*) AS c FROM answers a JOIN staff_queries q ON q.id=a.query_id "
        "WHERE a.status='pending_review'" + (" AND q.user_id=?" if user_id is not None else ""),
        params,
    ).fetchone()["c"]
    escalations = conn.execute(
        "SELECT COUNT(*) AS c FROM answers a JOIN staff_queries q ON q.id=a.query_id "
        "WHERE a.escalated=1" + (" AND q.user_id=?" if user_id is not None else ""),
        params,
    ).fetchone()["c"]
    return {
        "questions": questions,
        "answered": answered,
        "unanswered": unanswered,
        "pending_reviews": pending_reviews,
        "escalations": escalations,
        "helpful": feedback.get("helpful", 0),
        "not_helpful": feedback.get("not_helpful", 0),
        "active_policies": conn.execute(
            "SELECT COUNT(*) AS c FROM policy_documents WHERE status='approved'"
        ).fetchone()["c"],
        "pending_policies": conn.execute(
            "SELECT COUNT(*) AS c FROM policy_documents WHERE status='pending'"
        ).fetchone()["c"],
    }


def recent_audit(conn, limit: int = 12, actor: str | None = None):
    sql = "SELECT actor, action, entity, entity_id, detail, created_at FROM audit_log"
    params: list = []
    if actor:
        sql += " WHERE actor=?"
        params.append(actor)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_shares(conn):
    return [dict(r) for r in conn.execute("""
        SELECT s.id, s.document_id, s.user_id, s.created_at,
               d.title AS document_title, d.doc_code, d.version,
               u.username, COALESCE(u.display_name, u.username) AS customer_name
        FROM policy_shares s
        JOIN policy_documents d ON d.id=s.document_id
        JOIN users u ON u.id=s.user_id
        ORDER BY s.created_at DESC
    """).fetchall()]

def create_share(conn, document_id: int, user_id: int, shared_by: int):
    cur = conn.execute("INSERT INTO policy_shares(document_id,user_id,shared_by) VALUES(?,?,?)",
                       (document_id, user_id, shared_by))
    conn.commit()
    return cur.lastrowid

def delete_share(conn, share_id: int):
    cur = conn.execute("DELETE FROM policy_shares WHERE id=?", (share_id,))
    conn.commit()
    return cur.rowcount

def customer_shares(conn, user_id: int):
    return [dict(r) for r in conn.execute("""
        SELECT d.id, d.doc_code, d.title, d.version, d.status, d.updated_at,
               s.created_at AS shared_at
        FROM policy_shares s JOIN policy_documents d ON d.id=s.document_id
        WHERE s.user_id=? AND d.status='approved' ORDER BY s.created_at DESC
    """, (user_id,)).fetchall()]
