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
import re
from dataclasses import dataclass

from app.rag.retrieval import EvidenceChunk

logger = logging.getLogger(__name__)

# Models (e.g. anthropic/claude-sonnet-4.6 via OpenRouter) routinely wrap their
# JSON in a ```json ... ``` markdown fence even when response_format=json_object
# is requested, so we must strip the fence before parsing rather than rejecting
# an otherwise-valid answer. Citation-lock is unaffected: citations are still
# resolved by index against the evidence, never from the model's own text.
_FENCE_OPEN = re.compile(r"^```[a-zA-Z0-9]*\s*")
_FENCE_CLOSE = re.compile(r"\s*```$")
_FIRST_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class Citation:
    clause_number: str
    page_number: int | None
    filename: str
    quote_en: str


def parse_json_object(raw: str) -> dict | None:
    """Parses `raw` as a JSON object, returning None (never raising) on any
    malformed or non-object response - callers treat None as a refusal.
    Tolerates markdown code fences and surrounding prose the model may add."""
    if not raw:
        return None

    text = raw.strip()
    if text.startswith("```"):
        text = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text)).strip()

    parsed = _try_load_object(text)
    if parsed is None:
        # Last resort: extract the first {...} span (handles leading/trailing prose).
        match = _FIRST_OBJECT.search(text)
        if match:
            parsed = _try_load_object(match.group(0))

    if parsed is None:
        logger.warning("Could not parse a JSON object from LLM response: %r", raw)
    return parsed


def _try_load_object(text: str) -> dict | None:
    try:
        value = json.loads(text)
    except Exception:  # noqa: BLE001 - any parse failure degrades to None
        return None
    return value if isinstance(value, dict) else None


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
