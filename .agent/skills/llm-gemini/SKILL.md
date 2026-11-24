---
name: llm-gemini
description: LLM agent. Use for prompts, Gemini/Anthropic/OpenAI provider layer, JSON output validation, timeouts and abstain behaviour.
---
# LLM
Own: `backend/llm/prompts.py`, `backend/llm/provider.py`, validation in `backend/pipeline.py`, `prompts/PROMPT_PACK.md`.
- Gemini is instructor-approved. Env: `LLM_PROVIDER=gemini`, `GEMINI_API_KEY`, `LLM_MODEL` (default gemini-2.5-flash; if the key rejects it, use the model name shown in Google AI Studio).
- Every prompt change: bump `PROMPT_VERSION`, add a note in `scripts/export_prompt_pack.py`, run it, run all tests.
- Output JSON: `{answer, citations:[chunk ids], abstain, reason}`. Code rejects bad JSON, missing citations, citations not retrieved.
- Tasks left: run 10+ REAL Gemini calls on tests/test_questions.json types, record results in docs/TEST_EVIDENCE.md (live section), tune the prompt for Q22
  (other programme -> abstain), check Hinglish questions, confirm timeout and bad-key paths give `api_error`.
- Never log keys or provider response bodies. Mock is for tests only.
