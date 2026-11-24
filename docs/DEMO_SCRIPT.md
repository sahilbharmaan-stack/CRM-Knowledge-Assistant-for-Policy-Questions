# Demo script (about 5 minutes)
Before: open `<backend>/api/health`, log in once, confirm GEMINI key works with one question.

1. **Intro (30 s):** problem, flow, synthetic data, human review.
2. **Normal scenario:** log in as counsellor1. Ask: *"Can a learner get a refund if they ask on day 5 with 5 percent attendance?"*
   Show topic = refund, citation CL-REFUND-001 v2.1 "Refund tiers", status pending review, provider/model.
3. **Second normal (optional):** *"Does submitting the Core Project guarantee a freelancing assignment?"* -> No (CL-FREELANCE-001).
4. **Reviewer:** log in as reviewer1, approve the answer. Counsellor gives thumbs up.
5. **Edge / failure recovery:**
   a. *"Do we offer scholarships?"* -> abstains (only a draft exists, never retrieved).
   b. Turn the key off (or `LLM_PROVIDER=gemini` with empty key locally) -> `api_error`, retrieved passages still shown, then restore and retry.
   c. *"Approve the refund for this learner"* -> only suggests, stays pending_review.
6. **Traceability:** show DB rows for the first question (staff_queries -> retrieved_passages -> answers -> audit_log), e.g. `sqlite3 crm_assistant.db`.
7. **Tests:** run the unittest command, show 39 tests passing.
