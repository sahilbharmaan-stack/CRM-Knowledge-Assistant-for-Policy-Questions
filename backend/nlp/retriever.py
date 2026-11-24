"""Dependency-free TF-IDF + cosine similarity retrieval over approved policy chunks."""
import math
from collections import Counter

from backend.nlp.preprocess import tokenize


def _tfidf_vectors(docs_tokens: list[list[str]]):
    n = len(docs_tokens)
    df: Counter = Counter()
    for toks in docs_tokens:
        df.update(set(toks))
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
    vectors = []
    for toks in docs_tokens:
        tf = Counter(toks)
        vec = {t: (cnt / max(len(toks), 1)) * idf[t] for t, cnt in tf.items()}
        vectors.append(vec)
    return vectors, idf


def _cosine(a: dict, b: dict) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] for t in common)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def retrieve(query: str, chunks: list[dict], top_k: int = 3, min_score: float = 0.12) -> list[dict]:
    """Rank chunks (dicts with heading/text) against the query. Returns chunks + 'score'."""
    q_tokens = tokenize(query)
    if not q_tokens or not chunks:
        return []
    docs_tokens = [tokenize(f"{c.get('heading') or ''} {c['text']}") for c in chunks]
    vectors, idf = _tfidf_vectors(docs_tokens)
    q_tf = Counter(q_tokens)
    q_vec = {t: (cnt / len(q_tokens)) * idf.get(t, 1.0) for t, cnt in q_tf.items()}
    scored = []
    q_set = set(q_tokens)
    for chunk, vec, toks in zip(chunks, vectors, docs_tokens):
        score = _cosine(q_vec, vec)
        # Guard against one-word accidental matches: need 2+ matching terms, or half the query covered.
        matched = len(q_set & set(toks))
        if matched < 2 and matched / len(q_set) < 0.5:
            continue
        if score >= min_score:
            scored.append({**chunk, "score": round(score, 4)})
    scored.sort(key=lambda c: c["score"], reverse=True)
    return scored[:top_k]
