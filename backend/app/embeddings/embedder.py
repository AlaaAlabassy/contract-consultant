"""Local, free, multilingual embeddings via sentence-transformers.

Must be multilingual because questions arrive in Arabic while clause text is
in English - a pure-English embedding model would retrieve poorly against
Arabic queries. intfloat/multilingual-e5-* models expect "query: " / "passage: "
prefixes to get their best asymmetric retrieval quality (this is the model's
documented convention, not an arbitrary choice).
"""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    prefixed = [f"passage: {t}" for t in texts]
    return _model().encode(prefixed, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return _model().encode(f"query: {text}", normalize_embeddings=True).tolist()
