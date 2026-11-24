# Progress (updated 19 Nov 2026)

## Done
- Schema (6 tables + audit_log), sqlite3 CRUD, bootstrap (auto-creates DB, demo users, indexes policies)
- Synthetic handbook: 8 policy files (6 approved, 1 retired old refund version, 1 draft scholarship) + Word copy
- Validation, topic classifier (6 topics), TF-IDF retrieval with abstain guard
- LLM providers (Gemini, Claude, OpenAI, mock), JSON validation, prompt v1.1, prompt pack exported
- FastAPI + JWT with counsellor/reviewer roles, React UI, Render + Vercel config
- 39 offline tests passing (1 skipped: live LLM), sample DB, README, architecture, demo script

## Not yet verified (do next)
1. Run the real Gemini call (needs your key in .env) on 10+ questions; record results.
2. Start FastAPI locally and click through the UI (HTTP layer and frontend build not run in the build sandbox).
3. Deploy: Render backend, Vercel frontend, test the live link.
4. Put the instructor's approval message in docs/approval/APPROVALS.md.
5. Design polish with Mobbin references, optional animation.
6. Record the demo (normal + failure), push to GitHub, reply on the email thread by 24 Nov.


## Sprint log: premium UI + live analytics (AI Project Manager, 10 agents)
| Agent | Task | Result |
|---|---|---|
| manager | Plan, scope, review gating | Plan below, every task passed qa-security before done |
| data-db | `backend/analytics.py` aggregates, zero-filled daily series, scoped by user | done, no schema change |
| data-db | `backend/demo_seed.py` synthetic 30-day history, idempotent | done |
| backend-auth | `/api/analytics`, `/api/analytics/simulate` (admin only, audit logged) | done |
| nlp | Topic/confidence surfaced in UI and topic analytics | done |
| llm-gemini | Simulate uses offline mock provider, no key or quota used | done |
| frontend-ui | New design system, SVG charts, live polling, tweened animation | done |
| frontend-ui | Login, shell, Ask, History, Review, Knowledge, Users, Sharing, Audit, Settings | done |
| qa-security | 5 new tests (46 total green), Playwright run: login, KPI moved 128 -> 132 after live traffic, no console errors, mobile 390px checked | done |
| devops | `.env.example` SEED_DEMO_DATA, README, zip excludes `.venv` / `node_modules` | done |
Known limits: UI verified with esbuild bundle + Playwright against the real backend modules through a stdlib shim (FastAPI was not installable in the sandbox);
run `npm install && npm run build` and `uvicorn backend.main:app` locally to confirm the production build.
