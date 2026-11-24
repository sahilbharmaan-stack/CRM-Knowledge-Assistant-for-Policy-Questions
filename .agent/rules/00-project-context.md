# Project 037: CRM Knowledge Assistant (always-on rule)

Counsellor policy sawal puchta hai -> system approved policy docs se grounded answer deta hai (doc code + version).
Policy mein answer na ho -> **abstain**. Har answer human review (pending_review) mein jata hai.

## Current state (read docs/PROGRESS.md first)
The codebase ALREADY EXISTS and 39 tests pass. Agents improve, verify, harden and finish it. Do not rewrite from scratch.

## Real structure
```
backend/   main.py (FastAPI + JWT) pipeline.py db.py indexer.py auth.py bootstrap.py config.py
           nlp/ (preprocess, classifier, retriever)  llm/ (prompts.py, provider.py)
frontend/  React + Vite (src/main.jsx, src/api.js)     api/index.py  Vercel entry
data/policies/*.md   synthetic policies (format below)  data/policies_old_backup/  ignore
tests/ test_pipeline.py + test_questions.py + test_questions.json   sample/  sample DB
docs/ PROGRESS.md ARCHITECTURE.md DEMO_SCRIPT.md TEST_EVIDENCE.md CRM_Policy_Handbook_Synthetic.docx approval/
prompts/PROMPT_PACK.md (generated)   scripts/   schema.sql (READ-ONLY, source of truth)   render.yaml vercel.json
```

## Policy file format (indexer.py)
`# Title`, then `Doc-Code:`, `Version:`, `Status: approved|draft|retired`, `Category:` (refund, attendance,
programme, support, assessment, freelancing), then `## N. Section` headings. Only `approved` is retrieved.

## Approvals (docs/approval/APPROVALS.md)
Instructor approved: Gemini API, ChatGPT-generated synthetic data, PostgreSQL as fallback.
SQLite stays primary (brief requires sqlite3). Postgres only if online persistence is truly needed.

## Deployment plan
Instructor runs the DEPLOYED link in class (only to check learning). Frontend on Vercel, backend on Render free
(`render.yaml`, single process so SQLite stays consistent). Set `VITE_API_URL` on Vercel, `CORS_ORIGINS` on Render.
Free Render sleeps: open `/api/health` 5 minutes before class. DB auto-recreates on start (bootstrap).
Vercel-only deploy works but /tmp SQLite is per-instance and may lose data between requests.

## Hard rules
1. No API keys in code, chat, screenshots or git. Env vars only. `.env` is git-ignored.
2. Synthetic data only. Answers only from retrieved policy text. No evidence -> abstain.
3. App only suggests. Reviewer approves. Never approves refunds, sends messages, grades or edits production.
4. Real Gemini call in the final demo. Mock provider only in tests and offline work.
5. Every consequential step writes `audit_log`.
6. Never edit `schema.sql` or `data/policies_old_backup/`. Ask Manager before changing contracts or adding dependencies.
7. After any change run: `python -m unittest discover -s tests -p "test_*.py"` and keep it green.
8. Deadline 24 Nov 2026. Working end-to-end beats polish.
