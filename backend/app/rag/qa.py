"""Citation-lock question answering.

The model is shown a numbered list of retrieved clauses and is only ever
allowed to cite by that number - it never gets to invent its own quote text
or clause/page reference. The English quote shown to the user is always the
literal chunk text pulled from Chroma/Postgres, not anything the model wrote,
and any cited index outside the retrieved set is dropped (see
app/rag/citation_lock.py). This is what makes the "citation-lock" guarantee
enforceable in code rather than just a prompt instruction: an unsupported or
hallucinated answer collapses to a refusal instead of being trusted at face
value.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.config import settings
from app.rag.citation_lock import Citation, parse_json_object, resolve_citations
from app.rag.llm_client import chat_completion
from app.rag.retrieval import EvidenceChunk, retrieve

logger = logging.getLogger(__name__)

REFUSAL_TEXT_AR = "لا توجد أدلة كافية في العقد للإجابة على هذا السؤال بثقة."

SYSTEM_PROMPT = """أنت مساعد قانوني متخصص في عقود الإنشاءات (بأسلوب FIDIC). يصلك سؤال بالعربية ومجموعة مقتطفات مرقمة من نص العقد الأصلي بالإنجليزية فقط.

التزم بما يلي بدقة:
1. أجب بالعربية فقط، وبالاستناد إلى المقتطفات المرقمة المعطاة فقط - لا تستخدم أي معلومة أو معرفة خارجية.
2. إذا لم تكن المقتطفات كافية للإجابة بثقة، اجعل supported=false ولا تخترع إجابة.
3. ضع في citation_indices فقط أرقام المقتطفات التي استندت إليها فعلياً في إجابتك (لا تذكر رقماً لم تستخدمه).
4. أجب بصيغة JSON صارمة فقط، بدون أي نص خارج JSON، بالشكل التالي تماماً:
{"supported": true|false, "answer_ar": "...", "citation_indices": [1, 2]}"""


@dataclass
class Answer:
    answer_ar: str
    confidence: float
    confidence_label: str
    citations: list[Citation]


def answer_question(question: str, contract_id: int | None = None, top_k: int = 8) -> Answer:
    evidence = retrieve(question, top_k=top_k, contract_id=contract_id)
    if not evidence:
        return _refusal()

    try:
        raw = chat_completion(_build_messages(question, evidence))
    except Exception:  # noqa: BLE001 - any LLM call failure degrades to a refusal
        logger.exception("LLM call failed for question: %s", question)
        return _refusal()

    parsed = parse_json_object(raw)
    if parsed is None or not parsed.get("supported", False):
        return _refusal()

    citations, similarities = resolve_citations(parsed.get("citation_indices") or [], evidence)
    if not citations:
        return _refusal()  # claimed support but cited nothing verifiable

    answer_ar = (parsed.get("answer_ar") or "").strip()
    if not answer_ar:
        return _refusal()  # "supported" with no actual answer text is not usable

    confidence = min(similarities)
    return Answer(
        answer_ar=answer_ar,
        confidence=confidence,
        confidence_label=_label(confidence),
        citations=citations,
    )


def _build_messages(question: str, evidence: list[EvidenceChunk]) -> list[dict]:
    numbered = "\n\n".join(
        f"[{i}] الملف: {c.filename} | البند: {c.clause_number} {c.clause_title} | صفحة: {c.page_number}\n\"{c.text}\""
        for i, c in enumerate(evidence, start=1)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"المقتطفات:\n\n{numbered}\n\nالسؤال: {question}"},
    ]


def _label(confidence: float) -> str:
    if confidence >= settings.confidence_high:
        return "high"
    if confidence >= settings.confidence_warn:
        return "warn"
    if confidence >= settings.confidence_refuse:
        return "red"
    return "refuse"


def _refusal() -> Answer:
    return Answer(answer_ar=REFUSAL_TEXT_AR, confidence=0.0, confidence_label="refuse", citations=[])
