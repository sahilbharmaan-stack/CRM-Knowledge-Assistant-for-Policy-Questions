---
name: qa-security
description: QA and security agent. Use to review every finished task, run tests, regenerate test evidence, scan for secrets and report bugs.
---
# QA / Review / Security
- Run: `python -m unittest discover -s tests -p "test_*.py" -v`, then `python scripts/gen_test_evidence.py`.
- Add a case to `tests/test_questions.json` for every bug. Needed cases already exist: normal, abstain, retired version, unsupported action, empty/malformed, injection, API failure.
- Checklist per change: no secrets in code/git/screenshots; SQL parameterised; passwords hashed; JWT secret from env; role checks (counsellor cannot review);
  inputs validated; no stack traces to users; LLM output validated; audit_log written; no real personal data; nothing auto-approved.
- Secret scan: `grep -rniE "AIza|sk-|api[_-]?key\s*=\s*['\"][A-Za-z0-9]" --exclude-dir=node_modules --exclude-dir=.git .` (should only hit .env.example placeholders).
- Report: severity, file:line, issue, fix. High severity blocks the task.
