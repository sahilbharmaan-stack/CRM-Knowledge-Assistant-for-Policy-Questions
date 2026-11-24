---
name: devops
description: DevOps agent (activate Day 6). Use for Render backend, Vercel frontend, env vars, GitHub repo hygiene and a fresh-clone test.
---
# DevOps
- Render: `render.yaml` ready. Set `GEMINI_API_KEY`, `DEMO_PASSWORD`, `CORS_ORIGINS` in the dashboard. Health check `/api/health`.
- Vercel: import repo, set `VITE_API_URL` to the Render URL. Build is in `vercel.json`.
- Free Render sleeps (30-60 s cold start) and its disk resets; bootstrap recreates DB, users, policy index. Optional: UptimeRobot pings `/api/health` every 5 minutes.
- Pre-class checklist: open health URL, log in, ask 1 question, confirm provider=gemini in the answer.
- Repo hygiene: `.gitignore` has `.env`, `*.db` except `sample/*.db`. Run the secret scan before every push. Never commit keys.
- Final: clone fresh into a new folder, follow README exactly, run tests.
- Optional: GitHub Actions running the unittest command on push.
