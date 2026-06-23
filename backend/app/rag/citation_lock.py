"""Shared citation-lock primitives used by both QA (app/rag/qa.py) and risk
scanning (app/risk/scanner.py): parsing an LLM's JSON response defensively,
and resolving its claimed citation indices against the retrieved evidence
that was actually shown to it. An index is only trusted if it points at a
real evidence chunk - the quote text returned is always that chunk's literal
text, never anything the model wrote itself.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.rag.retrieval import EvidenceChunk

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    clause_number: str
    page_number: int | None
    filename: str
    quote_en: str


def parse_json_object(raw: str) -> dict | None:
    """Parses `raw` as a JSON object, returning None (never raising) on any
    malformed or non-object response - callers treat None as a refusal."""
    try:
        parsed = json.loads(raw)
    except Exception:  # noqa: BLE001 - any parse failure degrades to None
        logger.exception("Failed to parse LLM response as JSON: %r", raw)
        return None
    if not isinstance(parsed, dict):
        logger.warning("LLM response is not a JSON object: %r", raw)
        return None
    return parsed


def resolve_citations(
    indices: object, evidence: list[EvidenceChunk]
) -> tuple[list[Citation], list[float]]:
    """Resolves model-claimed citation indices (1-based) against `evidence`.
    Out-of-range, wrong-typed, or duplicate indices are silently dropped
    rather than trusted - this is the enforcement point for citation-lock."""
    if not isinstance(indices, list):
        indices = []

    citations: list[Citation] = []
    similarities: list[float] = []
    seen: set[int] = set()
    for i in indices:
        if isinstance(i, bool) or not isinstance(i, int) or not (1 <= i <= len(evidence)):
            continue
        if i in seen:
            continue
        seen.add(i)
        chunk = evidence[i - 1]
        citations.append(
            Citation(
                clause_number=chunk.clause_number,
                page_number=chunk.page_number,
                filename=chunk.filename,
                quote_en=chunk.text,
            )
        )
        similarities.append(chunk.similarity)
    return citations, similarities
