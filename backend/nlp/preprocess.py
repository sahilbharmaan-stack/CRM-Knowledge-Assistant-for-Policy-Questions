"""Text cleaning, validation and tokenization."""
import re
import unicodedata

from backend import config

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "in", "on", "for", "and",
    "or", "if", "it", "this", "that", "do", "does", "can", "i", "we", "you", "my", "me", "what",
    "how", "when", "which", "with", "at", "by", "from", "as", "will", "should", "student",
    "learner", "please", "tell", "about",
    "learners", "students", "get", "any", "many", "much", "need", "needed", "take", "we", "they",
    "who", "there", "have", "has", "our", "us", "offer", "give", "right", "now", "tell", "all",
}


class QueryValidationError(ValueError):
    """Raised when a staff query fails validation."""


def validate_query(text) -> str:
    if text is None or not isinstance(text, str):
        raise QueryValidationError("Query must be text.")
    cleaned = clean_text(text)
    if not cleaned:
        raise QueryValidationError("Query is empty.")
    if len(cleaned) < config.MIN_QUERY_CHARS:
        raise QueryValidationError("Query is too short to understand.")
    if len(cleaned) > config.MAX_QUERY_CHARS:
        raise QueryValidationError(f"Query is too long (max {config.MAX_QUERY_CHARS} characters).")
    if not re.search(r"[A-Za-z]{2,}", cleaned):
        raise QueryValidationError("Query has no readable words.")
    return cleaned


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)  # control characters
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS and len(w) > 1]


def stem(word: str) -> str:
    """Very small suffix stemmer; enough for policy vocabulary."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word
