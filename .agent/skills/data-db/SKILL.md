---
name: data-db
description: Data and SQLite agent. Use for policy markdown files, indexer, db.py CRUD, sample database, useful SQL queries and data checks.
---
# Data / DB
Own: `data/policies/*.md`, `backend/db.py`, `backend/indexer.py`, `backend/bootstrap.py`, `scripts/make_sample_db.py`, `sample/`.
- `schema.sql` is READ-ONLY. Need a change? Ask Manager first.
- Parameterised SQL only (`?`). Foreign keys on. Every status change also calls `db.audit`.
- Policies: keep the file format from the rules file. One approved version per doc code is the norm; retired/draft stay in DB but are never retrieved.
- Tasks left: add `backend/queries.sql` (abstain rate, pending reviews, answers by topic, feedback by doc), refresh the sample DB after data changes
  (`python scripts/make_sample_db.py`), keep `docs/CRM_Policy_Handbook_Synthetic.docx` in sync (`python scripts/build_handbook_docx.py`).
- If online persistence becomes necessary, a Postgres adapter is approved but build it only on Manager's request (Day 6+).
