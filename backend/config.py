"""Central configuration. All secrets come from environment variables, never from code."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "data" / "policies"


def _load_dotenv() -> None:
    """Tiny .env loader (local dev only). .env is git-ignored."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def get(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


# LLM provider: groq | gemini | anthropic | openai | mock
LLM_PROVIDER = get("LLM_PROVIDER", "mock")
LLM_MODEL = get("LLM_MODEL", "")
LLM_TIMEOUT_SECONDS = int(get("LLM_TIMEOUT_SECONDS", "20"))

# Retrieval
MIN_SCORE = float(get("MIN_RETRIEVAL_SCORE", "0.12"))
TOP_K = int(get("TOP_K", "3"))

# Query validation
MIN_QUERY_CHARS = 5
MAX_QUERY_CHARS = 500

# Auth
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(get("JWT_EXPIRE_MINUTES", "120"))


def jwt_secret() -> str:
    secret = get("JWT_SECRET")
    if secret:
        return secret
    if get("VERCEL"):
        raise RuntimeError("JWT_SECRET must be set in Vercel environment variables")
    return "dev-only-secret-change-me-0123456789abcdef"  # local development only
