"""Synthetic demo activity (30 days of questions, reviews, feedback) so charts have history.

Synthetic data only: no real learner data. Enabled with SEED_DEMO_DATA=1; runs once
(marker stored in app_settings) and never touches approved policy text.
Run manually:  python -m backend.demo_seed
"""
import json
import random
import secrets
from datetime import datetime, timedelta, timezone

from backend import auth, db

QUESTIONS = {
    "refund": ["Can a learner get a refund after day 5 with 5% attendance?",
               "What deduction applies if a student cancels in week two?",
               "How long does a refund take to reach the learner?"],
    "attendance": ["What is the attendance requirement for a student?",
                   "Can a missed live session be made up from the recording?",
                   "What happens if attendance falls below the minimum?"],
    "programme": ["Can a student transfer to the next batch?", "What is the programme duration?",
                  "When is the certificate issued?"],
    "support": ["What is the support response time for a ticket?", "How do I escalate a complaint?",
                "What are the helpdesk hours?"],
    "assessment": ["How many resubmissions are allowed for an assignment?",
                   "What is the pass mark for the final assessment?", "Can a learner appeal a result?"],
    "freelancing": ["Does submitting the Core Project guarantee a freelancing assignment?",
                    "Who qualifies for freelancing allocation?"],
    "other": ["Can you book a meeting room for tomorrow?"],
}
WEIGHTS = {"refund": 26, "attendance": 22, "programme": 15, "support": 13, "assessment": 12,
           "freelancing": 8, "other": 4}
DEMO_PEOPLE = (("demo.asha", "Asha Verma"), ("demo.rohan", "Rohan Mehta"),
               ("demo.priya", "Priya Nair"), ("demo.kabir", "Kabir Singh"))


def seed_demo_activity(conn, days: int = 30, seed: int = 7) -> int:
    if db.get_setting(conn, "demo_seeded") == "1":
        return 0
    rnd = random.Random(seed)
    user_ids = []
    for username, name in DEMO_PEOPLE:
        existing = db.get_user_by_username(conn, username)
        # random unusable password: demo accounts exist only to own synthetic rows
        user_ids.append(existing["id"] if existing else db.create_user(
            conn, username, auth.hash_password(secrets.token_urlsafe(24)), "counsellor", name))
    chunks = {}
    for r in conn.execute("SELECT c.id, c.topic, c.document_id FROM policy_chunks c "
                          "JOIN policy_documents d ON d.id=c.document_id WHERE d.status='approved'"):
        chunks.setdefault(r["topic"], []).append(r["id"])
    reviewer = conn.execute("SELECT id FROM users WHERE role IN ('administrator','reviewer') LIMIT 1").fetchone()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    topics, weights = list(WEIGHTS), list(WEIGHTS.values())
    created = 0
    for back in range(days - 1, -1, -1):
        day = now - timedelta(days=back)
        weekday = day.weekday()
        volume = int(rnd.gauss(9 if weekday < 5 else 3, 2) + (days - back) * 0.12)  # gentle growth
        for _ in range(max(1, volume)):
            topic = rnd.choices(topics, weights)[0]
            hour = min(23, max(0, int(rnd.gauss(13, 3.2))))
            if back == 0 and hour > now.hour:
                hour = now.hour
            ts = day.replace(hour=hour, minute=rnd.randint(0, 59), second=rnd.randint(0, 59))
            roll = rnd.random()
            abstain = topic == "other" or roll < 0.11
            error = not abstain and roll > 0.975
            status = "api_error" if error else "abstained" if abstain else "answered"
            cur = conn.execute(
                "INSERT INTO staff_queries (user_id, query_text, cleaned_text, topic, topic_confidence, status, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (rnd.choice(user_ids), rnd.choice(QUESTIONS[topic]), "", topic,
                 round(rnd.uniform(0.45, 0.97), 2), status, ts.strftime("%Y-%m-%d %H:%M:%S")))
            qid = cur.lastrowid
            picks = rnd.sample(chunks.get(topic, []), k=min(3, len(chunks.get(topic, []))))
            for rank, cid in enumerate(picks, 1):
                conn.execute("INSERT INTO retrieved_passages (query_id, chunk_id, rank, score) VALUES (?,?,?,?)",
                             (qid, cid, rank, round(rnd.uniform(0.18, 0.74) / rank ** 0.4, 3)))
            latency = int(rnd.lognormvariate(6.9, 0.55))
            reviewed = back > 0 and rnd.random() < 0.85
            decision = "rejected" if reviewed and rnd.random() < 0.08 else "approved" if reviewed else "pending_review"
            feedback = None
            if decision == "approved" and not abstain and rnd.random() < 0.6:
                feedback = "helpful" if rnd.random() < 0.82 else "not_helpful"
            reviewed_at = (ts + timedelta(minutes=rnd.randint(4, 240))).strftime("%Y-%m-%d %H:%M:%S") if reviewed else None
            conn.execute(
                "INSERT INTO answers (query_id, answer_text, citations_json, abstained, provider, model, latency_ms,"
                " prompt_version, status, feedback, reviewed_by, reviewed_at, escalated, error, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (qid, None if error else "Synthetic demo answer grounded in the cited policy passage.",
                 json.dumps([]), int(abstain), "gemini", "gemini-2.5-flash", latency, "v1", decision, feedback,
                 reviewer["id"] if reviewed and reviewer else None, reviewed_at, int(rnd.random() < 0.03),
                 "Upstream timeout (synthetic)" if error else None, ts.strftime("%Y-%m-%d %H:%M:%S")))
            created += 1
    conn.commit()
    db.set_setting(conn, "demo_seeded", "1")
    db.audit(conn, "system", "demo_activity_seeded", detail=f"{created} synthetic questions")
    return created


if __name__ == "__main__":
    from backend.bootstrap import bootstrap
    c = db.connect()
    bootstrap(c)
    print("Seeded", seed_demo_activity(c), "synthetic questions")
