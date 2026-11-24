"""Writes prompts/PROMPT_PACK.md from backend/llm/prompts.py so docs never drift from code."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.llm import prompts  # noqa: E402

demo = prompts.build_user_prompt(
    "Can a learner get a refund on day 5 with 5 percent attendance?",
    [{"id": 12, "doc_code": "CL-REFUND-001", "version": "2.1", "heading": "2. Refund tiers",
      "text": "Tier A: request within 7 days of enrolment and attendance below 10 percent ..."}])
out = f"""# Prompt Pack (version {prompts.PROMPT_VERSION})

## System prompt
```
{prompts.SYSTEM_PROMPT}
```

## Task prompt template (built per request)
```
{demo}
```

## Expected output schema
```json
{prompts.expected_schema()}
```

## Validation applied in code (backend/pipeline.py)
Valid JSON object; `abstain` is boolean; non-abstain answers need non-empty text and at least one
citation; every citation must be one of the retrieved passage ids; otherwise the system abstains safely.

## Version notes
- v1.0: first version. Grounded answers, JSON output, abstain rule, injection guard, 2 examples.
- v1.1: exact-number rule, document code and version in answers, learner-specific facts must be verified,
  wrong-programme abstain rule, Hinglish allowed, example updated to refund tiers of CL-REFUND-001 v2.1.
- v1.2: contradictory passages must abstain. The assistant does not pick a side or invent a policy.
"""
(ROOT / "prompts").mkdir(exist_ok=True)
(ROOT / "prompts" / "PROMPT_PACK.md").write_text(out, encoding="utf-8")
print("written")
