# Architecture and workflow

```mermaid
flowchart LR
  U[Counsellor / Reviewer<br/>React UI on Vercel] -->|HTTPS + JWT| API[FastAPI backend<br/>Render]
  subgraph Python modules
    API --> V[nlp.preprocess<br/>validate + clean]
    V --> C[nlp.classifier<br/>topic]
    C --> R[nlp.retriever<br/>TF-IDF + cosine]
    R --> P[pipeline.py<br/>prompt + output validation]
  end
  P -->|prompt v1.1| L[(LLM API<br/>Gemini approved)]
  L --> P
  API <--> DB[(SQLite<br/>6 tables + audit_log)]
  M[CRM connector boundary<br/>SQLite mirror / policy files] -->|index approved docs| DB
  P -->|pending_review| H[Human reviewer approves or rejects]
```

**Connector boundary:** policies enter only through `backend/indexer.py` from files in `data/policies`
(a mirror/export). The app never reads or writes a production CRM or LMS.

**Statuses:** query = received / answered / abstained / api_error / rejected;
answer = pending_review / approved / rejected. Every step writes `audit_log`.

**Trace for one question:** `staff_queries` (topic, confidence) -> `retrieved_passages` (rank, score) ->
`answers` (provider, model, latency, citations, prompt_version) -> `audit_log`.
