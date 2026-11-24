"""LLM provider layer: Gemini / Anthropic Claude / OpenAI over plain HTTPS (stdlib only) + a mock.

Every provider returns (text, meta) and raises LLMError on any failure, so the pipeline can
recover safely. Keys are read from environment variables only.
"""
import json
import time
import urllib.error
import urllib.request

from backend import config


class LLMError(RuntimeError):
    """Any API failure: missing key, timeout, HTTP error, malformed response."""


DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",         # override with LLM_MODEL if your key uses another model
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
}


def _post_json(url: str, headers: dict, body: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code} from provider") from e  # body not logged: may echo secrets
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LLMError(f"Network/timeout error: {type(e).__name__}") from e
    except json.JSONDecodeError as e:
        raise LLMError("Provider returned non-JSON response") from e


def _require_key(env_name: str) -> str:
    key = config.get(env_name)
    if not key:
        raise LLMError(f"{env_name} is not set")
    return key


def call_gemini(system: str, user: str, model: str, timeout: int):
    key = _require_key("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    data = _post_json(url, {"x-goog-api-key": key}, body, timeout)
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected Gemini response shape") from e


def call_anthropic(system: str, user: str, model: str, timeout: int):
    key = _require_key("ANTHROPIC_API_KEY")
    body = {"model": model, "max_tokens": 600, "temperature": 0.1, "system": system,
            "messages": [{"role": "user", "content": user}]}
    data = _post_json("https://api.anthropic.com/v1/messages",
                      {"x-api-key": key, "anthropic-version": "2023-06-01"}, body, timeout)
    try:
        return data["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected Anthropic response shape") from e


def call_openai(system: str, user: str, model: str, timeout: int):
    key = _require_key("OPENAI_API_KEY")
    body = {"model": model, "temperature": 0.1, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    data = _post_json("https://api.openai.com/v1/chat/completions",
                      {"Authorization": f"Bearer {key}"}, body, timeout)
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected OpenAI response shape") from e



def call_groq(system: str, user: str, model: str, timeout: int):
    """Call Groq's OpenAI-compatible Chat Completions API."""
    key = _require_key("GROQ_API_KEY")
    body = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    data = _post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"Authorization": f"Bearer {key}"},
        body,
        timeout,
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected Groq response shape") from e


def call_mock(system: str, user: str, model: str, timeout: int):
    """Offline deterministic provider for tests/demo-without-key: quotes the top passage."""
    import re
    m = re.search(r'<passage id="(\d+)"[^>]*>\n(.*?)\n</passage>', user, re.S)
    if not m:
        return json.dumps({"answer": "", "citations": [], "abstain": True, "reason": "no passages"})
    return json.dumps({"answer": m.group(2).strip()[:400], "citations": [int(m.group(1))],
                       "abstain": False, "reason": "mock provider quoted top passage"})


PROVIDERS = {"gemini": call_gemini, "anthropic": call_anthropic, "openai": call_openai, "groq": call_groq, "mock": call_mock}


def generate(system: str, user: str, provider: str | None = None, model: str | None = None):
    """Return (text, meta). Raises LLMError."""
    provider = (provider or config.LLM_PROVIDER or "mock").lower()
    if provider not in PROVIDERS:
        raise LLMError(f"Unknown provider '{provider}'")
    model = model or config.LLM_MODEL or DEFAULT_MODELS.get(provider, "mock")
    start = time.monotonic()
    text = PROVIDERS[provider](system, user, model, config.LLM_TIMEOUT_SECONDS)
    meta = {"provider": provider, "model": model, "latency_ms": int((time.monotonic() - start) * 1000)}
    return text, meta
