---
description: Full security and quality review before commit or submission
---

1. qa-security: scan repo for secrets (keys, tokens, .env, db with real data).
2. Run `pytest` and report pass/fail table into `docs/test_evidence.md`.
3. Run the review checklist from the qa-security skill on all changed files.
4. Verify abstain and human-review behaviour manually with 1 normal and 1 failure scenario.
5. Report findings to Manager; block commit on any high severity issue.
