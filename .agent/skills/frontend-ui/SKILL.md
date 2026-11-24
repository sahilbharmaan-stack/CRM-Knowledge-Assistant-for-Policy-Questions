---
name: frontend-ui
description: Frontend agent. Use for React UI/UX, design polish, animation, optional light 3D hero, and Mobbin design references.
---
# Frontend + UI/UX + Animation
Own: `frontend/` (React + Vite; `src/main.jsx`, `src/api.js`). API base from `VITE_API_URL` (empty = same origin).
1. Before changing any screen, use the Mobbin MCP server to collect 2-3 references each for: login, Q&A answer card with citation chips, review queue,
   history, empty/error states. Write short notes in `docs/design/<screen>.md`. Inspiration only; never copy a brand's assets or exact layout. If Mobbin is unavailable say so once and use the `frontend-design` skill.
2. Must show: answer, citation chips (doc code, version, section), topic badge, status (pending review / abstained / api_error), feedback buttons,
   reviewer approve/reject, clear abstain message, loading and error states, mobile-friendly, AA contrast.
3. Add Framer Motion (`npm i framer-motion`) for card reveal and chip stagger; keep optional 3D hero lazy-loaded with `prefers-reduced-motion` fallback. Core flow must never depend on it.
4. Verify with `npm run build`. No secrets in frontend code.
