PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('administrator', 'policy_manager', 'counsellor', 'reviewer')),
    display_name  TEXT,
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS policy_documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_code     TEXT NOT NULL,
    title        TEXT NOT NULL,
    version      TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'draft'
                 CHECK (status IN ('draft', 'pending', 'approved', 'rejected', 'archived', 'retired')),
    source_path  TEXT,
    review_note  TEXT,
    submitted_by INTEGER REFERENCES users(id),
    reviewed_by  INTEGER REFERENCES users(id),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (doc_code, version)
);

CREATE TABLE IF NOT EXISTS policy_chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES policy_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    heading     TEXT,
    text        TEXT NOT NULL,
    topic       TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS staff_queries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    query_text       TEXT NOT NULL,
    cleaned_text     TEXT,
    topic            TEXT,
    topic_confidence REAL,
    status           TEXT NOT NULL DEFAULT 'received'
                     CHECK (status IN ('received', 'answered', 'abstained', 'api_error', 'rejected')),
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS retrieved_passages (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER NOT NULL REFERENCES staff_queries(id) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL REFERENCES policy_chunks(id),
    rank     INTEGER NOT NULL,
    score    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id         INTEGER NOT NULL REFERENCES staff_queries(id) ON DELETE CASCADE,
    answer_text      TEXT,
    citations_json   TEXT NOT NULL DEFAULT '[]',
    abstained        INTEGER NOT NULL DEFAULT 0,
    provider         TEXT,
    model            TEXT,
    latency_ms       INTEGER,
    prompt_version   TEXT,
    status           TEXT NOT NULL DEFAULT 'pending_review'
                     CHECK (status IN ('pending_review', 'approved', 'rejected')),
    feedback         TEXT CHECK (feedback IN ('helpful', 'not_helpful') OR feedback IS NULL),
    feedback_note    TEXT,
    reviewed_by      INTEGER REFERENCES users(id),
    reviewed_at      TEXT,
    review_note      TEXT,
    escalated        INTEGER NOT NULL DEFAULT 0 CHECK (escalated IN (0, 1)),
    escalation_note  TEXT,
    error            TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    actor      TEXT NOT NULL,
    action     TEXT NOT NULL,
    entity     TEXT,
    entity_id  INTEGER,
    detail     TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_chunks_topic ON policy_chunks(topic);
CREATE INDEX IF NOT EXISTS idx_queries_user ON staff_queries(user_id);
CREATE INDEX IF NOT EXISTS idx_passages_query ON retrieved_passages(query_id);
CREATE INDEX IF NOT EXISTS idx_answers_query ON answers(query_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
