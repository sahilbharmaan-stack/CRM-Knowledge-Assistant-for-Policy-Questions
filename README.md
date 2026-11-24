# Project: CRM Knowledge Assistant for Policy Questions

A counsellor asks a policy question (refund, attendance, programme, support, assessment, freelancing).
The system finds the relevant approved policy passages and an LLM writes a **grounded answer with
document and version citations**. If the policy text does not contain the answer, it **abstains**.
Every answer waits for **human review**. The app never approves refunds or sends messages.

**Flow:** index approved policies -> validate query -> classify topic -> TF-IDF retrieval -> LLM (JSON) ->
validate output -> save to SQLite -> reviewer approves/rejects -> feedback.

## Stack
Python 3.11+, FastAPI, sqlite3, PyJWT auth (roles: counsellor, reviewer), own TF-IDF/cosine retrieval,
Gemini API (approved by instructor; Anthropic/OpenAI also supported), React (Vite) frontend.

## Setup (local)
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit: LLM_PROVIDER=gemini, GEMINI_API_KEY=..., DEMO_PASSWORD=...
python -m backend.bootstrap                            # creates DB, demo users, indexes policies
# from frontend/; this starts both the API and Vite together
npm run dev                                             # open http://localhost:5173
```
On Windows PowerShell:
```powershell
Set-Location frontend
npm install
npm run dev
```
Keep this terminal open while using the app. `npm run dev:vite` starts only the frontend and requires the API to be started separately.
The app automatically provisions an initial administrator on first database startup. Default local credentials are **admin / Admin@CRM2026!**. Before first launch on a real deployment, override `ADMIN_USERNAME`, `ADMIN_PASSWORD`, and `ADMIN_DISPLAY_NAME` in `.env` (or deployment environment variables) with unique values. Do not use the sample credentials on a public deployment. Optional demo accounts can be seeded only when `SEED_DEMO_USERS=1` and a secure `DEMO_PASSWORD` are configured. Use `LLM_PROVIDER=mock` to run fully offline. The final demo can use the approved Gemini provider.

## Tests (no network, uses mock provider)
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
39 tests: 17 pipeline/DB/auth tests + 22 data-driven cases from `tests/test_questions.json`
(normal, abstain, retired-version, unsupported action, empty/malformed input, injection, API failure).
Results and expected vs actual: `docs/TEST_EVIDENCE.md`.

## Folder structure
```
backend/      main.py (API), pipeline.py (workflow), db.py, indexer.py, auth.py, nlp/, llm/
frontend/     React UI          data/policies/  synthetic approved policies (md)
prompts/      PROMPT_PACK.md    tests/          unit + data-driven tests
sample/       sample SQLite DB  docs/           handbook, architecture, demo script, approvals
schema.sql    DB schema         render.yaml, vercel.json   deployment
```

## Sample data provenance
All policy text is **synthetic**, generated with ChatGPT and accepted by the instructor. It is not real
company policy. Source of truth: `data/policies/*.md`; Word copy: `docs/CRM_Policy_Handbook_Synthetic.docx`.
Document statuses: approved (retrieved), draft and retired (never retrieved). No real learner data exists.

## LLM approval and key handling
Gemini use and PostgreSQL fallback were approved by the instructor (`docs/approval/APPROVALS.md`).
Keys come only from environment variables (`.env` is git-ignored). Timeout 20 s, errors recorded as
`api_error`, retrieved passages still shown. Provider, model, latency and prompt version are stored per answer.

## Ask a question: quick prompts and welcome voice

The Ask a question workspace includes ready-to-use prompts grouped into Refunds & payments, Freelancing & projects, Attendance & leave, and Learning & support. Selecting a prompt fills the question composer; the user still submits it normally. Answers remain grounded in approved policy documents and follow the existing review workflow.

After a successful sign-in, the browser attempts to play a short welcome message using its built-in speech synthesis. A **Welcome voice** control in the top bar lets users replay it. Voice availability and playback depend on the browser and device speech settings; no audio file or external voice service is required.

## Deployment (frontend on Vercel, backend on Render)
1. Render: New > Blueprint from this repo (`render.yaml`). Set `GEMINI_API_KEY`, `DEMO_PASSWORD`,
   `CORS_ORIGINS=<your vercel url>`.
2. Vercel: import repo, set `VITE_API_URL=<render url>`. Build is defined in `vercel.json`.
3. Before a demo open `<render url>/api/health` to wake the free service (30-60 s).
Known limitation: free Render sleeps and its disk resets on restart. The app recreates the DB, users and
policy index automatically; earlier queries and reviews are lost. Next step: managed Postgres (approved fallback).

## Assumptions, limitations, next steps
- Keyword topic classifier and TF-IDF retrieval (no embeddings). Next: embeddings and reranking.
- Single-language policies (English); Hinglish questions work through shared vocabulary only.
- The CRM connector is a SQLite mirror (`policy_documents`, `policy_chunks`); no production system is touched.
- Next: policy upload and approval UI, Postgres, analytics on abstain rate and feedback.

## Workspace features (enhanced UI)
- **Operations overview:** live question, answer, unanswered, review, escalation and policy counts; helpful-feedback rate; recent question activity.
- **CSV snapshot export:** download the dashboard metrics for reporting and sharing.
- **Knowledge base workspace:** search policy documents, filter by lifecycle status, upload PDF/DOCX/TXT/Markdown policy files (8 MB maximum), and submit drafts for approval.
- **Governed publishing:** uploaded documents remain drafts and are excluded from approved-policy retrieval until the existing approval workflow publishes them.
- **First-run administrator setup:** create the initial administrator securely through the existing one-time setup endpoint; once an administrator exists, setup is closed.
- **Administrator audit trail:** inspect recent sign-in, account, policy and review events.
- **Role-aware navigation:** dashboard and approved policy access for staff; policy management and answer review controls for authorized roles; audit trail restricted to administrators.
- **Answer history:** load saved citations from the API response and preserve the original policy/version references.

The dashboard and policy management screens use the existing FastAPI endpoints and SQLite schema; no new third-party runtime dependency or database migration is required. The frontend production build should be run with `npm install && npm run build` in `frontend/` before deployment.


## Administrator control panel (enhanced)

The administrator account opens the role-aware control panel with Overview, User Management, Knowledge Library, Sharing Centre, and Audit Trail. All roles use the same login form; the API detects the account role from the supplied username and password. Public self-registration is disabled.

### Create customer accounts
1. Sign in with the administrator credentials configured in `.env` (the default local setup is `admin` / `Admin@CRM2026!`).
2. Open **User management** and create an account.
3. Choose a unique username, a password of at least 10 characters, and the role: **Customer**, **Reviewer**, or **Policy manager**. The administrator sets each account password; passwords are stored as secure hashes.
4. The user signs in on the same login page. The role is detected automatically from the account; public self-registration is disabled.

### Share approved policies
1. Upload a policy from **Knowledge library** and submit it for review.
2. Once the policy is approved, open **Sharing centre**.
3. Select the approved document and an active customer account, then share it.
4. Customers see assigned documents under **Shared with me**. Administrators can revoke a share from the register.

Sharing records are stored in the SQLite `policy_shares` table and created/revoked actions are written to the audit log. Existing databases are upgraded automatically at startup.

## Premium UI refinement

The administrator control panel and customer/staff workspace include a refined visual system with a deep navy-and-champagne admin palette, subtle animated orbit artwork, elevated dashboard cards, responsive navigation, refined forms and tables, and reduced-motion support. All roles sign in from the same form; the UI follows the role returned by the API.

To build the frontend locally:

```bash
cd frontend
npm ci
npm run build
```


## Premium UI + live analytics (v2)

One design system for every role (Customer, Reviewer, Policy manager, Administrator): dark navy sidebar, brass accent,
Instrument Serif + Hanken Grotesk type, responsive down to phones, keyboard focus and `prefers-reduced-motion` respected.

**Analytics are computed live from SQLite** (`backend/analytics.py`, `GET /api/analytics?days=7|14|30|90`). Nothing is cached or hard-coded:
- KPIs with period-over-period change and sparklines: questions, answer rate, average response (p50/p95), helpful rate, awaiting review.
- Stacked area chart of daily volume by outcome (answered / abstained / error) with hover crosshair and a live end-point.
- Topic donut, weekday x hour heat map, most relied-on policies, response-time histogram, review pipeline and turnaround, grounding ring, most active accounts, live activity feed.
- The page polls every 8 s (paused while the tab is hidden); charts glide to new values. A "New data" flash appears when the database fingerprint changes.
- Counsellors see only their own activity; staff and administrators see the whole workspace. CSV export of the daily series.
- Administrators get **Send live traffic**: pushes a few real questions through the real pipeline using the offline mock provider (no API quota) so you can watch every chart move during a demo. Audit logged.

**Demo history:** set `SEED_DEMO_DATA=1` (once) or run `python -m backend.demo_seed` to add 30 days of synthetic questions, reviews and feedback owned by four non-loginable `demo.*` accounts. Synthetic only.

**Other fixes:** answer history now keeps its saved citations (the API returns `citations`, the old UI read `citations_json`); Knowledge library gained Approve / Reject / Archive for authorised roles; Settings page (model name, approval toggle, example-secret warning); escalate button for customers; audit trail filter and auto-refresh.

Tests: `python -m unittest discover -s tests -p "test_*.py" -v` (46 tests, 5 new analytics tests).


## Groq API setup

Set `LLM_PROVIDER=groq`, `LLM_MODEL=llama-3.3-70b-versatile`, and `GROQ_API_KEY`
in the project-root `.env` file (copy `.env.example` first). Keep `.env` out of Git.
The backend uses Groq's OpenAI-compatible Chat Completions endpoint. The API key is
read server-side only; do not put it in frontend environment variables.
