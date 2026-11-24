"""Keyword-weighted policy topic classifier (refund | attendance | programme | support | assessment | freelancing | other)."""
from backend.nlp.preprocess import tokenize

TOPIC_KEYWORDS = {
    "refund": ["refund", "cancel", "cancellation", "money", "fee", "payment", "reimburse",
               "deduction", "chargeback", "withdraw"],
    "attendance": ["attendance", "absent", "absence", "present", "class", "session", "miss",
                   "leave", "late", "shortage", "makeup", "recording"],
    "programme": ["programme", "program", "course", "certificate", "duration", "eligibility",
                  "syllabus", "batch", "module", "enrol", "enroll", "transfer", "project"],
    "support": ["support", "ticket", "helpdesk", "escalation", "complaint", "response",
                "issue", "contact", "login", "access", "sla", "portal", "hours"],
    "assessment": ["assessment", "exam", "quiz", "assignment", "score", "marks", "pass", "result",
                   "resubmission", "resubmit", "appeal", "viva", "grade", "deadline"],
    "freelancing": ["freelancing", "freelance", "allocation", "allocate", "eligible", "qualify",
                    "qualification", "core"],
}
TOPIC_STEMS = {t: {tokenize(k)[0] for k in kws if tokenize(k)} for t, kws in TOPIC_KEYWORDS.items()}


def classify_topic(text: str) -> tuple[str, float]:
    """Return (topic, confidence 0-1). Unknown text -> ('other', 0.0)."""
    tokens = tokenize(text)
    if not tokens:
        return "other", 0.0
    scores = {t: sum(1 for tok in tokens if tok in stems) for t, stems in TOPIC_STEMS.items()}
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    if scores[best] == 0:
        return "other", 0.0
    return best, round(scores[best] / total, 2)
