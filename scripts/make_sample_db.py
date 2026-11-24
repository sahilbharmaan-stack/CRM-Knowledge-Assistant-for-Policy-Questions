"""Builds sample/crm_assistant_sample.db with policies, demo users and a few example Q&A rows.
Uses the offline mock provider, so the rows are illustrative. The live demo uses the real API."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["LLM_PROVIDER"] = "mock"
os.environ["SEED_DEMO_USERS"] = "1"
os.environ.setdefault("DEMO_PASSWORD", "demo-pass-123")

from backend import db, pipeline  # noqa: E402
from backend.bootstrap import bootstrap  # noqa: E402

out = ROOT / "sample" / "crm_assistant_sample.db"
out.parent.mkdir(exist_ok=True)
if out.exists():
    out.unlink()
conn = db.connect(str(out))
bootstrap(conn)
counsellor = dict(db.get_user_by_username(conn, "counsellor1"))
reviewer = db.get_user_by_username(conn, "reviewer1")
qs = ["Can a learner get a refund if they ask on day 5 with 5 percent attendance?",
      "What is the minimum attendance required to complete the programme?",
      "Does submitting the Core Project guarantee a freelancing assignment?",
      "What is on the hostel food menu on Sundays?", "   "]
results = [pipeline.ask(conn, counsellor, q, "mock") for q in qs]
first = results[0]
db.set_feedback(conn, first["answer_id"], "helpful", "Clear and cited")
db.review_answer(conn, first["answer_id"], reviewer["id"], "approved")
print("sample db written:", out)
for r in results:
    print(r["status"], "-", r.get("answer") or r.get("message"))
conn.close()
