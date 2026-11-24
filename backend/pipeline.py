"""End-to-end workflow:
validate -> classify -> retrieve -> LLM grounded answer -> validate -> persist -> human review.

The assistant only SUGGESTS policy answers. Nothing is approved/sent automatically:
every answer is stored as 'pending_review'.
"""
import json
import re

from backend import config, db
from backend.llm import prompts
from backend.llm.provider import LLMError, generate
from backend.nlp.classifier import classify_topic
from backend.nlp.preprocess import QueryValidationError, validate_query
from backend.nlp.retriever import retrieve

ABSTAIN_TEXT = "I could not find this in the approved policy documents. Please escalate to a policy owner."
CONFLICT_TEXT = (
    "The approved policy passages conflict, so I cannot confirm the answer. "
    "Please ask a policy owner to resolve the documents."
)


def conflicting_versions(hits: list[dict]) -> list[str]:
    """Document codes whose retrieved passages come from more than one version."""
    versions: dict[str, set] = {}
    for hit in hits:
        versions.setdefault(hit["doc_code"], set()).add(hit["version"])
    return sorted(code for code, found in versions.items() if len(found) > 1)


def parse_llm_json(text: str, allowed_ids: set[int]) -> dict:
    """Validate the model output. Raises ValueError if it is not trustworthy."""
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fenced:
        text = fenced.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError("LLM output is not valid JSON") from e
    if not isinstance(data, dict):
        raise ValueError("LLM output is not a JSON object")
    abstain = data.get("abstain")
    answer = data.get("answer", "")
    citations = data.get("citations", [])
    if not isinstance(abstain, bool):
        raise ValueError("'abstain' must be boolean")
    if not isinstance(answer, str) or not isinstance(citations, list):
        raise ValueError("'answer' must be text and 'citations' a list")
    if not all(isinstance(c, int) for c in citations):
        raise ValueError("citations must be integers")
    if abstain:
        return {"answer": "", "citations": [], "abstain": True, "reason": str(data.get("reason", ""))}
    if not answer.strip():
        raise ValueError("empty answer without abstain")
    if not citations:
        raise ValueError("answer has no citations (ungrounded)")
    if not set(citations) <= allowed_ids:
        raise ValueError("citation refers to a passage that was not retrieved")
    return {"answer": answer.strip(), "citations": citations, "abstain": False,
            "reason": str(data.get("reason", ""))}


def ask(conn, user: dict, raw_query, provider: str | None = None) -> dict:
    """Run the full workflow. Always returns a result dict; never raises for user/API errors."""
    actor = user["username"]
    # 1. validate
    try:
        cleaned = validate_query(raw_query)
    except QueryValidationError as e:
        qid = db.create_query(conn, user["id"], str(raw_query)[:500] if raw_query else "",
                              status="rejected")
        db.audit(conn, actor, "query_rejected", "staff_queries", qid, str(e))
        return {"status": "rejected", "message": str(e), "query_id": qid}

    # 2. classify
    topic, confidence = classify_topic(cleaned)
    qid = db.create_query(conn, user["id"], cleaned, cleaned, topic, confidence)
    db.audit(conn, actor, "query_received", "staff_queries", qid, f"topic={topic}")

    # 3. retrieve (topic-filtered first, then all approved chunks as fallback)
    pool = db.approved_chunks(conn, topic if topic != "other" else None)
    hits = retrieve(cleaned, pool, config.TOP_K, config.MIN_SCORE)
    if not hits and topic != "other":
        hits = retrieve(cleaned, db.approved_chunks(conn), config.TOP_K, config.MIN_SCORE)
    for rank, h in enumerate(hits, 1):
        db.add_passage(conn, qid, h["id"], rank, h["score"])

    base = {"query_id": qid, "topic": topic, "topic_confidence": confidence,
            "passages": [{"chunk_id": h["id"], "doc_code": h["doc_code"], "version": h["version"],
                          "heading": h["heading"], "score": h["score"]} for h in hits]}

    # 4. no policy text, or two approved versions of the same document -> abstain WITHOUT calling the LLM
    conflict = conflicting_versions(hits)
    if conflict:
        aid = db.create_answer(conn, qid, CONFLICT_TEXT, [], True, prompt_version=prompts.PROMPT_VERSION)
        db.set_query_status(conn, qid, "abstained")
        db.audit(conn, actor, "abstained_conflict", "answers", aid, ",".join(conflict))
        return {**base, "status": "abstained", "answer_id": aid, "answer": CONFLICT_TEXT,
                "citations": [], "message": CONFLICT_TEXT, "review_status": "pending_review"}

    if not hits:
        aid = db.create_answer(conn, qid, ABSTAIN_TEXT, [], True, prompt_version=prompts.PROMPT_VERSION)
        db.set_query_status(conn, qid, "abstained")
        db.audit(conn, actor, "abstained_no_policy", "answers", aid)
        return {**base, "status": "abstained", "answer_id": aid, "answer": ABSTAIN_TEXT,
                "citations": [], "review_status": "pending_review"}

    # 5. LLM grounded answer
    user_prompt = prompts.build_user_prompt(cleaned, hits)
    try:
        chosen_model = (db.get_setting(conn, "llm_model") or "").strip() or None
        text, meta = generate(prompts.SYSTEM_PROMPT, user_prompt, provider, chosen_model)
    except LLMError as e:
        aid = db.create_answer(conn, qid, None, [], False, prompt_version=prompts.PROMPT_VERSION,
                               error=str(e))
        db.set_query_status(conn, qid, "api_error")
        db.audit(conn, actor, "llm_error", "answers", aid, str(e))
        return {**base, "status": "api_error", "answer_id": aid, "answer": None, "citations": [],
                "message": "AI service unavailable. Retrieved policy passages are shown for manual reading.",
                "review_status": "pending_review"}

    # 6. validate output
    allowed = {h["id"] for h in hits}
    try:
        parsed = parse_llm_json(text, allowed)
    except ValueError as e:
        aid = db.create_answer(conn, qid, ABSTAIN_TEXT, [], True, meta["provider"], meta["model"],
                               meta["latency_ms"], prompts.PROMPT_VERSION, error=f"invalid output: {e}")
        db.set_query_status(conn, qid, "abstained")
        db.audit(conn, actor, "llm_output_rejected", "answers", aid, str(e))
        return {**base, "status": "abstained", "answer_id": aid, "answer": ABSTAIN_TEXT,
                "citations": [], "message": "Model output failed validation; abstained safely.",
                "review_status": "pending_review"}

    # 7. persist
    if parsed["abstain"]:
        aid = db.create_answer(conn, qid, ABSTAIN_TEXT, [], True, meta["provider"], meta["model"],
                               meta["latency_ms"], prompts.PROMPT_VERSION)
        db.set_query_status(conn, qid, "abstained")
        db.audit(conn, actor, "abstained_by_model", "answers", aid, parsed["reason"])
        return {**base, "status": "abstained", "answer_id": aid, "answer": ABSTAIN_TEXT,
                "citations": [], "provider": meta["provider"], "model": meta["model"],
                "review_status": "pending_review"}

    cited = [{"chunk_id": h["id"], "doc_code": h["doc_code"], "version": h["version"],
              "heading": h["heading"]} for h in hits if h["id"] in parsed["citations"]]
    aid = db.create_answer(conn, qid, parsed["answer"], cited, False, meta["provider"], meta["model"],
                           meta["latency_ms"], prompts.PROMPT_VERSION)
    db.set_query_status(conn, qid, "answered")
    db.audit(conn, actor, "answer_generated", "answers", aid,
             f"{meta['provider']}/{meta['model']} {meta['latency_ms']}ms")
    return {**base, "status": "answered", "answer_id": aid, "answer": parsed["answer"],
            "citations": cited, "provider": meta["provider"], "model": meta["model"],
            "latency_ms": meta["latency_ms"], "review_status": "pending_review"}
