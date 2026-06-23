"""Citation-lock risk scanning.

For each rule in the catalog, retrieves the clauses most relevant to that
risk topic and asks the LLM to confirm or deny the risk against only those
clauses. Mirrors app/rag/qa.py's citation-lock pattern (see
app/rag/citation_lock.py for the shared parsing/resolution logic): a rule
only produces a finding if the LLM both confirms it and cites at least one
verifiable clause. A single rule's LLM failure is logged and skipped rather
than aborting the whole scan, since the other rules are independent checks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.rag.citation_lock import Citation, parse_json_object, resolve_citations
from app.rag.llm_client import chat_completion
from app.rag.retrieval import EvidenceChunk, retrieve
from app.risk.catalog import RISK_CATALOG, RiskRule

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """أنت محلل مخاطر متخصص في عقود الإنشاءات (بأسلوب FIDIC). يصلك وصف لخطر تعاقدي محدد ومجموعة مقتطفات مرقمة من نص العقد الأصلي بالإنجليزية فقط.

التزم بدقة:
1. حدد وجود الخطر بالاستناد إلى المقتطفات المعطاة فقط - لا تستخدم أي معرفة خارجية.
2. اجعل present=true فقط إذا أكدت المقتطفات وجود هذا الخطر تحديداً في هذا العقد.
3. ضع في citation_indices فقط أرقام المقتطفات التي تؤكد الخطر فعلياً (لا تذكر رقماً لم تستخدمه).
4. أجب بصيغة JSON صارمة فقط، بدون أي نص خارج JSON، بالشكل التالي تماماً:
{"present": true|false, "explanation_ar": "...", "citation_indices": [1, 2]}"""


@dataclass
class RiskFinding:
    rule_key: str
    severity: str
    explanation_ar: str
    confidence: float
    citations: list[Citation]


def scan_contract(contract_id: int, top_k: int = 4) -> list[RiskFinding]:
    findings: list[RiskFinding] = []
    for rule in RISK_CATALOG:
        finding = _check_rule(rule, contract_id, top_k)
        if finding is not None:
            findings.append(finding)
    return findings


def _check_rule(rule: RiskRule, contract_id: int, top_k: int) -> RiskFinding | None:
    evidence = retrieve(rule.query_ar, top_k=top_k, contract_id=contract_id)
    if not evidence:
        return None

    try:
        raw = chat_completion(_build_messages(rule, evidence))
    except Exception:  # noqa: BLE001 - one rule's failure must not abort the scan
        logger.exception("LLM call failed while checking risk rule %s", rule.rule_key)
        return None

    parsed = parse_json_object(raw)
    if parsed is None or not parsed.get("present", False):
        return None

    citations, similarities = resolve_citations(parsed.get("citation_indices") or [], evidence)
    if not citations:
        return None  # claimed risk present but cited nothing verifiable

    explanation_ar = (parsed.get("explanation_ar") or "").strip()
    if not explanation_ar:
        return None

    return RiskFinding(
        rule_key=rule.rule_key,
        severity=rule.severity,
        explanation_ar=explanation_ar,
        confidence=min(similarities),
        citations=citations,
    )


def _build_messages(rule: RiskRule, evidence: list[EvidenceChunk]) -> list[dict]:
    numbered = "\n\n".join(
        f"[{i}] الملف: {c.filename} | البند: {c.clause_number} {c.clause_title} | صفحة: {c.page_number}\n\"{c.text}\""
        for i, c in enumerate(evidence, start=1)
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"الخطر المطلوب فحصه: {rule.description_ar}\n\nالمقتطفات:\n\n{numbered}",
        },
    ]
