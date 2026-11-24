"""FastAPI app: JWT auth, policy lifecycle, and grounded Q&A. Mounted under /api."""
import json
import re
from threading import Lock

import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from backend import accounts, analytics, auth, config, db, pipeline
from backend.bootstrap import bootstrap
from backend.documents import DocumentError, MAX_BYTES, policy_from_upload
from backend.llm.provider import DEFAULT_MODELS
from backend.nlp.classifier import classify_topic

app = FastAPI(title="CRM Knowledge Assistant", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=(config.get("CORS_ORIGINS", "http://localhost:5173")).split(","),
    allow_methods=["*"], allow_headers=["*"],
)
bearer = HTTPBearer(auto_error=False)
CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,39}$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,19}$")
EXAMPLE_SECRETS = {"change-me-to-a-long-random-string", "dev-only-secret-change-me-0123456789abcdef", "change-me"}
_bootstrap_lock = Lock()


def get_conn():
    conn = db.connect()
    try:
        with _bootstrap_lock:
            bootstrap(conn)
        yield conn
    finally:
        conn.close()


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), conn=Depends(get_conn)):
    if not cred:
        raise HTTPException(401, "Missing token")
    try:
        payload = auth.decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get_user(conn, int(payload["sub"]))
    if not user or not user["active"]:
        raise HTTPException(401, "This account is deactivated or unknown")
    return dict(user)


def require(*roles):
    def dependency(user=Depends(current_user)):
        if user["role"] not in roles:
            raise HTTPException(403, "You do not have permission for this action")
        return user
    return dependency


def _public_user(user) -> dict:
    return {
        "id": user["id"], "username": user["username"], "role": user["role"],
        "display_name": user["display_name"], "active": bool(user["active"]),
    }


def _can_decide_policy(user, conn) -> bool:
    if user["role"] == "administrator":
        return True
    return user["role"] in ("policy_manager", "reviewer") and db.get_setting(conn, "policy_manager_can_approve") == "1"


def _owns(user, owner_id: int) -> bool:
    return user["role"] != "counsellor" or user["id"] == owner_id


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)
    panel: str = Field(default="any", pattern="^(any|admin|customer|staff)$")


class SetupIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")
    password: str = Field(min_length=10, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")
    password: str = Field(min_length=10, max_length=200)
    role: str
    display_name: str | None = Field(default=None, max_length=80)


class UserPatch(BaseModel):
    role: str | None = None
    active: bool | None = None
    display_name: str | None = Field(default=None, max_length=80)


class AskIn(BaseModel):
    query: str = Field(max_length=2000)


class FeedbackIn(BaseModel):
    feedback: str = Field(pattern="^(helpful|not_helpful)$")
    note: str | None = Field(default=None, max_length=500)


class ReviewIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = Field(default=None, max_length=500)


class EscalateIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class PolicyDecisionIn(BaseModel):
    decision: str = Field(pattern="^(approved|rejected|archived)$")
    reason: str = Field(min_length=3, max_length=500)


class SettingsIn(BaseModel):
    llm_model: str | None = Field(default=None, max_length=80)
    policy_manager_can_approve: bool | None = None


def _issue_session(user) -> dict:
    return {
        "token": auth.create_token(user["id"], user["username"], user["role"]),
        "id": user["id"],
        "role": user["role"],
        "username": user["username"],
        "display_name": user["display_name"],
        "active": bool(user["active"]),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "provider": config.LLM_PROVIDER}


@app.get("/api/auth/status")
def auth_status(conn=Depends(get_conn)):
    return {"needs_setup": db.count_users(conn) == 0}


@app.post("/api/auth/setup")
def setup(body: SetupIn, conn=Depends(get_conn)):
    if db.count_users(conn):
        raise HTTPException(409, "An administrator already exists. Sign in instead.")
    problem = accounts.password_problem(body.password, body.username)
    if problem:
        raise HTTPException(400, problem)
    user_id = db.create_user(conn, body.username, auth.hash_password(body.password),
                             "administrator", body.display_name.strip())
    db.audit(conn, body.username, "admin_setup", "users", user_id)
    user = db.get_user(conn, user_id)
    return _issue_session(user)


@app.post("/api/auth/login")
def login(body: LoginIn, conn=Depends(get_conn)):
    user = db.get_user_by_username(conn, body.username.strip())
    if not user or not auth.verify_password(body.password, user["password_hash"]):
        db.audit(conn, body.username.strip(), "login_failed")
        raise HTTPException(401, "Invalid username or password")
    if not user["active"]:
        db.audit(conn, body.username.strip(), "login_failed", detail="inactive_account")
        raise HTTPException(403, "This account is deactivated")
    if body.panel == "admin" and user["role"] != "administrator":
        raise HTTPException(403, "These credentials do not belong to an administrator account")
    if body.panel == "customer" and user["role"] != "counsellor":
        raise HTTPException(403, "These credentials do not belong to a customer account")
    if body.panel == "staff" and user["role"] not in ("reviewer", "policy_manager"):
        raise HTTPException(403, "These credentials do not belong to a staff account")
    if not user["active"]:
        db.audit(conn, user["username"], "login_blocked")
        raise HTTPException(401, "This account is deactivated")
    db.audit(conn, user["username"], "login_ok")
    return _issue_session(user)


@app.get("/api/me")
def me(user=Depends(current_user), conn=Depends(get_conn)):
    return {
        **_public_user(user),
        "can_review_answers": user["role"] in accounts.ANSWER_REVIEWERS,
        "can_edit_policies": user["role"] in accounts.POLICY_EDITORS,
        "can_decide_policies": _can_decide_policy(user, conn),
    }


@app.post("/api/auth/password")
def change_password(body: PasswordIn, user=Depends(current_user), conn=Depends(get_conn)):
    if not auth.verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(400, "Current password is incorrect")
    problem = accounts.password_problem(body.new_password, user["username"])
    if problem:
        raise HTTPException(400, problem)
    if body.new_password == body.current_password:
        raise HTTPException(400, "Choose a different password")
    db.set_password(conn, user["id"], auth.hash_password(body.new_password))
    db.audit(conn, user["username"], "password_changed", "users", user["id"])
    return {"ok": True}


@app.get("/api/users")
def users(_user=Depends(require("administrator")), conn=Depends(get_conn)):
    return db.list_users(conn)


@app.post("/api/users")
def create_staff(body: UserIn, user=Depends(require("administrator")), conn=Depends(get_conn)):
    if body.role not in accounts.ROLES:
        raise HTTPException(400, "Unknown role")
    problem = accounts.password_problem(body.password, body.username)
    if problem:
        raise HTTPException(400, problem)
    if db.get_user_by_username(conn, body.username):
        raise HTTPException(409, "That username already exists")
    user_id = db.create_user(conn, body.username, auth.hash_password(body.password),
                             body.role, (body.display_name or "").strip() or None)
    db.audit(conn, user["username"], "user_created", "users", user_id, body.role)
    return db.list_users(conn)


@app.patch("/api/users/{user_id}")
def patch_user(user_id: int, body: UserPatch, user=Depends(require("administrator")), conn=Depends(get_conn)):
    target = db.get_user(conn, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    if body.role is not None and body.role not in accounts.ROLES:
        raise HTTPException(400, "Unknown role")
    try:
        accounts.assert_keeps_an_admin(conn, user_id, body.role, body.active)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    db.update_user(conn, user_id, body.role, None if body.active is None else int(body.active), body.display_name)
    db.audit(conn, user["username"], "user_updated", "users", user_id,
             json.dumps({"role": body.role, "active": body.active}))
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(user=Depends(current_user), conn=Depends(get_conn)):
    scope = user["id"] if user["role"] == "counsellor" else None
    counts = db.dashboard_counts(conn, scope)
    counts["recent"] = db.recent_audit(conn, 8, user["username"] if scope else None)
    counts["role"] = user["role"]
    return counts


@app.get("/api/analytics")
def analytics_snapshot(days: int = 14, user=Depends(current_user), conn=Depends(get_conn)):
    """Live aggregates. Counsellors only see their own activity; staff and admins see everything."""
    if days not in (7, 14, 30, 90):
        raise HTTPException(400, "days must be 7, 14, 30 or 90")
    scope = user["id"] if user["role"] == "counsellor" else None
    data = analytics.snapshot(conn, scope, days)
    data["scope"] = "personal" if scope else "workspace"
    return data


class SimulateIn(BaseModel):
    count: int = Field(default=3, ge=1, le=5)


@app.post("/api/analytics/simulate")
def simulate_traffic(body: SimulateIn, user=Depends(require("administrator")), conn=Depends(get_conn)):
    """Push a few real questions through the real pipeline (offline mock provider, no API quota)
    so the live dashboard visibly moves during a demo. Admin only, audit logged."""
    import random
    from backend.demo_seed import QUESTIONS
    pool = [q for qs in QUESTIONS.values() for q in qs]
    done = []
    for text in random.sample(pool, k=body.count):
        res = pipeline.ask(conn, user, text, "mock")
        done.append({"query": text, "status": res.get("status"), "topic": res.get("topic")})
    db.audit(conn, user["username"], "demo_traffic_simulated", "staff_queries", detail=f"{len(done)} questions")
    return {"ok": True, "created": done}


@app.post("/api/ask")
def ask(body: AskIn, user=Depends(current_user), conn=Depends(get_conn)):
    return pipeline.ask(conn, user, body.query)


@app.get("/api/history")
def history(q: str | None = None, status: str | None = None, user=Depends(current_user), conn=Depends(get_conn)):
    allowed = {"received", "answered", "abstained", "api_error", "rejected"}
    if status and status not in allowed:
        raise HTTPException(400, "Unknown status")
    scope = user["id"] if user["role"] == "counsellor" else None
    rows = db.history(conn, scope, 80, (q or "").strip() or None, status)
    for row in rows:
        row["citations"] = json.loads(row.pop("citations_json") or "[]")
        row["escalated"] = bool(row["escalated"])
    return rows


@app.get("/api/policies")
def policies(q: str | None = None, status: str | None = None, user=Depends(current_user), conn=Depends(get_conn)):
    approved_only = user["role"] == "counsellor"
    return db.list_documents(conn, status, (q or "").strip() or None, approved_only)


@app.get("/api/policies/{document_id}")
def policy_detail(document_id: int, user=Depends(current_user), conn=Depends(get_conn)):
    document = db.get_document(conn, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    if user["role"] == "counsellor" and document["status"] != "approved":
        raise HTTPException(403, "You can only read approved policies")
    payload = dict(document)
    payload["sections"] = db.document_chunks(conn, document_id)
    return payload


@app.post("/api/policies/upload")
async def upload_policy(
    file: UploadFile = File(...),
    doc_code: str = Form(...),
    title: str = Form(...),
    version: str = Form(...),
    user=Depends(require(*accounts.POLICY_EDITORS)),
    conn=Depends(get_conn),
):
    doc_code, title, version = doc_code.strip(), title.strip(), version.strip()
    filename = (file.filename or "").strip() or "policy.txt"
    if not CODE_RE.match(doc_code) or not VERSION_RE.match(version):
        raise HTTPException(400, "Use letters, numbers, dots, or dashes for the code and version")
    if not title:
        raise HTTPException(400, "Title is required")
    if db.find_document(conn, doc_code, version):
        raise HTTPException(409, "That document code and version already exists. Upload a new version.")
    data = await file.read(MAX_BYTES + 1)
    try:
        parsed = policy_from_upload(filename, data, doc_code, title, version)
    except DocumentError as e:
        raise HTTPException(400, str(e)) from e
    # Save the document, all sections and the audit entry atomically.
    try:
        conn.execute("BEGIN")
        document_id = db.insert_document(
            conn, parsed["doc_code"], parsed["title"], parsed["version"], filename, "draft", user["id"], commit=False
        )
        for index, (heading, section_text) in enumerate(parsed["sections"]):
            topic = parsed.get("category") or classify_topic(f"{parsed['title']} {heading} {section_text}")[0]
            db.add_chunk(conn, document_id, index, heading, section_text, topic, commit=False)
        db.audit(conn, user["username"], "policy_uploaded", "policy_documents", document_id, filename, commit=False)
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        # Log server-side for diagnosis without leaking internals to the client.
        import logging
        logging.getLogger(__name__).exception("Policy upload database processing failed")
        raise HTTPException(500, "The document was parsed but could not be saved. Check server logs and database schema.") from e
    return {"id": document_id, "status": "draft", "sections": len(parsed["sections"])}


@app.post("/api/policies/{document_id}/submit")
def submit_policy(document_id: int, user=Depends(require(*accounts.POLICY_EDITORS)), conn=Depends(get_conn)):
    document = db.get_document(conn, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    if document["status"] not in ("draft", "rejected"):
        raise HTTPException(400, "Only a draft or rejected document can be submitted")
    db.mark_submitted(conn, document_id, user["id"])
    db.audit(conn, user["username"], "policy_submitted", "policy_documents", document_id)
    return {"ok": True, "status": "pending"}


@app.post("/api/policies/{document_id}/decision")
def decide_policy(document_id: int, body: PolicyDecisionIn, user=Depends(current_user), conn=Depends(get_conn)):
    if not _can_decide_policy(user, conn):
        raise HTTPException(403, "You are not authorized to approve or reject policies")
    document = db.get_document(conn, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    if body.decision == "archived":
        if document["status"] not in ("approved", "retired"):
            raise HTTPException(400, "Only an approved policy can be archived")
    elif document["status"] != "pending":
        raise HTTPException(400, "Only a policy waiting for approval can be approved or rejected")
    status = "archived" if body.decision == "archived" else body.decision
    db.set_document_status(conn, document_id, status, user["id"], body.reason.strip())
    db.audit(conn, user["username"], f"policy_{status}", "policy_documents", document_id, body.reason.strip())
    return {"ok": True, "status": status}


@app.post("/api/answers/{answer_id}/feedback")
def feedback(answer_id: int, body: FeedbackIn, user=Depends(current_user), conn=Depends(get_conn)):
    answer = db.get_answer_context(conn, answer_id)
    if not answer:
        raise HTTPException(404, "Answer not found")
    if not _owns(user, answer["user_id"]):
        raise HTTPException(403, "You can only rate your own answers")
    db.set_feedback(conn, answer_id, body.feedback, body.note)
    db.audit(conn, user["username"], "feedback", "answers", answer_id, body.feedback)
    return {"ok": True}


@app.post("/api/answers/{answer_id}/escalate")
def escalate(answer_id: int, body: EscalateIn, user=Depends(current_user), conn=Depends(get_conn)):
    answer = db.get_answer_context(conn, answer_id)
    if not answer:
        raise HTTPException(404, "Answer not found")
    if not _owns(user, answer["user_id"]):
        raise HTTPException(403, "You can only request review of your own answers")
    db.escalate_answer(conn, answer_id, (body.note or "").strip() or None)
    db.audit(conn, user["username"], "review_requested", "answers", answer_id, body.note)
    return {"ok": True}


@app.post("/api/answers/{answer_id}/review")
def review(answer_id: int, body: ReviewIn, user=Depends(require(*accounts.ANSWER_REVIEWERS)), conn=Depends(get_conn)):
    if not db.get_answer(conn, answer_id):
        raise HTTPException(404, "Answer not found")
    if body.decision == "rejected" and not (body.reason or "").strip():
        raise HTTPException(400, "A reason is required when rejecting an answer")
    note = (body.reason or "").strip() or None
    db.review_answer(conn, answer_id, user["id"], body.decision, note)
    db.audit(conn, user["username"], f"review_{body.decision}", "answers", answer_id, note)
    return {"ok": True}


@app.get("/api/settings")
def get_settings(_user=Depends(require("administrator")), conn=Depends(get_conn)):
    provider = (config.LLM_PROVIDER or "mock").lower()
    stored_model = (db.get_setting(conn, "llm_model") or "").strip()
    secret = config.jwt_secret()
    return {
        "llm_provider": provider,
        "llm_model": stored_model or config.LLM_MODEL or DEFAULT_MODELS.get(provider, ""),
        "model_is_override": bool(stored_model),
        "gemini_configured": bool(config.get("GEMINI_API_KEY")),
        "anthropic_configured": bool(config.get("ANTHROPIC_API_KEY")),
        "openai_configured": bool(config.get("OPENAI_API_KEY")),
        "groq_configured": bool(config.get("GROQ_API_KEY")),
        "jwt_secret_is_example": secret in EXAMPLE_SECRETS,
        "policy_manager_can_approve": db.get_setting(conn, "policy_manager_can_approve") == "1",
    }


@app.patch("/api/settings")
def patch_settings(body: SettingsIn, user=Depends(require("administrator")), conn=Depends(get_conn)):
    if body.llm_model is not None:
        model = body.llm_model.strip()
        if model and not re.fullmatch(r"[A-Za-z0-9._:-]{2,80}", model):
            raise HTTPException(400, "Model name contains unsupported characters")
        db.set_setting(conn, "llm_model", model)
    if body.policy_manager_can_approve is not None:
        db.set_setting(conn, "policy_manager_can_approve", "1" if body.policy_manager_can_approve else "0")
    db.audit(conn, user["username"], "settings_updated", "app_settings")
    return get_settings(user, conn)


@app.get("/api/shares")
def shares(_user=Depends(require("administrator")), conn=Depends(get_conn)):
    return db.list_shares(conn)


class ShareIn(BaseModel):
    document_id: int
    user_id: int


@app.post("/api/shares")
def add_share(body: ShareIn, user=Depends(require("administrator")), conn=Depends(get_conn)):
    document = db.get_document(conn, body.document_id)
    customer = db.get_user(conn, body.user_id)
    if not document or document["status"] != "approved":
        raise HTTPException(400, "Only approved policies can be shared")
    if not customer or customer["role"] != "counsellor" or not customer["active"]:
        raise HTTPException(400, "Choose an active customer account")
    try:
        share_id = db.create_share(conn, body.document_id, body.user_id, user["id"])
    except Exception as exc:
        if "UNIQUE" in str(exc):
            raise HTTPException(409, "This policy is already shared with that customer") from exc
        raise
    db.audit(conn, user["username"], "policy_shared", "policy_documents", body.document_id,
             f"Shared with {customer['username']}")
    return {"ok": True, "id": share_id}


@app.delete("/api/shares/{share_id}")
def remove_share(share_id: int, user=Depends(require("administrator")), conn=Depends(get_conn)):
    if not db.delete_share(conn, share_id):
        raise HTTPException(404, "Share not found")
    db.audit(conn, user["username"], "policy_share_revoked", "policy_shares", share_id)
    return {"ok": True}


@app.get("/api/shared-policies")
def my_shared_policies(user=Depends(require("counsellor")), conn=Depends(get_conn)):
    return db.customer_shares(conn, user["id"])


@app.get("/api/audit")
def audit_log(_user=Depends(require("administrator")), conn=Depends(get_conn)):
    return db.recent_audit(conn, 100)
