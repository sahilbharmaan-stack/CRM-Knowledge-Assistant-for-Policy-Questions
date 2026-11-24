---
name: backend-auth
description: Backend agent. Use for FastAPI routes, JWT auth, roles, validation, error handling, pipeline wiring and Render run setup.
---
# Backend + Auth
Own: `backend/main.py`, `auth.py`, `config.py`, `pipeline.py` (workflow part), `api/index.py`.
- Endpoints exist: /api/health, /auth/login, /ask, /history, /policies, /answers/{id}/feedback, /answers/{id}/review (reviewer only).
- Tasks left: run the server locally (`uvicorn backend.main:app`) and smoke test every endpoint with curl (FastAPI was not installed in the build sandbox, so HTTP layer is untested);
  add a counsellor-gets-403-on-review test using FastAPI TestClient (needs `httpx`); add login rate limit if time; make sure errors never leak stack traces.
- JWT secret from env (`JWT_SECRET`). Set `CORS_ORIGINS` to the Vercel URL on Render. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
