"""Edge-case coverage for citation-lock risk scanning (app/risk/scanner.py).

Mirrors test_qa.py's approach: refuse/skip whenever evidence or confirmation
is missing, and a single rule's failure must never abort the whole scan
since the rules are independent checks against the same contract.
"""

import json

from app.risk import scanner
from app.risk.catalog import RiskRule
from app.risk.scanner import _check_rule, scan_contract
from app.rag.retrieval import EvidenceChunk

RULE = RiskRule(
    rule_key="unlimited_liability",
    query_ar="حد المسؤولية",
    description_ar="عدم وجود حد أعلى للمسؤولية.",
    severity="high",
)

EVIDENCE = [
    EvidenceChunk(
        chunk_id="1:0",
        text="The Contractor's liability shall be unlimited under this Contract.",
        similarity=0.88,
        filename="contract.pdf",
        clause_number="17.6",
        clause_title="Limitation of Liability",
        page_number=20,
    )
]


def _stub_llm(monkeypatch, response_obj=None, raise_exc=None):
    def fake_chat_completion(messages):
        if raise_exc:
            raise raise_exc
        return json.dumps(response_obj)

    monkeypatch.setattr(scanner, "chat_completion", fake_chat_completion)


def _stub_retrieval(monkeypatch, evidence=EVIDENCE):
    monkeypatch.setattr(scanner, "retrieve", lambda query, top_k=4, contract_id=None: evidence)


def test_no_evidence_yields_no_finding(monkeypatch):
    _stub_retrieval(monkeypatch, evidence=[])
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is None


def test_llm_exception_yields_no_finding_not_a_crash(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, raise_exc=RuntimeError("network error"))
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is None


def test_present_false_yields_no_finding(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"present": False, "explanation_ar": "غير موجود", "citation_indices": [1]},
    )
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is None


def test_present_true_without_valid_citation_yields_no_finding(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"present": True, "explanation_ar": "موجود", "citation_indices": [99]},
    )
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is None


def test_present_true_with_blank_explanation_yields_no_finding(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"present": True, "explanation_ar": "   ", "citation_indices": [1]},
    )
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is None


def test_valid_finding_has_literal_quote_and_min_similarity_confidence(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={
            "present": True,
            "explanation_ar": "العقد لا يحدد سقفاً لمسؤولية المتعاقد.",
            "citation_indices": [1],
        },
    )
    result = _check_rule(RULE, contract_id=1, top_k=4)
    assert result is not None
    assert result.rule_key == "unlimited_liability"
    assert result.severity == "high"
    assert result.confidence == EVIDENCE[0].similarity
    assert result.citations[0].quote_en == EVIDENCE[0].text


def test_one_failing_rule_does_not_abort_the_whole_scan(monkeypatch):
    rule_ok = RiskRule(rule_key="rule_ok", query_ar="q1", description_ar="d1", severity="medium")
    rule_fails = RiskRule(rule_key="rule_fails", query_ar="q2", description_ar="d2", severity="low")
    monkeypatch.setattr(scanner, "RISK_CATALOG", [rule_fails, rule_ok])

    monkeypatch.setattr(scanner, "retrieve", lambda query, top_k=4, contract_id=None: EVIDENCE)

    calls = {"n": 0}

    def fake_chat_completion(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated failure for the first rule")
        return json.dumps(
            {"present": True, "explanation_ar": "خطر مؤكد", "citation_indices": [1]}
        )

    monkeypatch.setattr(scanner, "chat_completion", fake_chat_completion)

    findings = scan_contract(contract_id=1, top_k=4)

    assert len(findings) == 1
    assert findings[0].rule_key == "rule_ok"


def test_scan_contract_returns_empty_list_when_no_risks_found(monkeypatch):
    monkeypatch.setattr(scanner, "RISK_CATALOG", [RULE])
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, response_obj={"present": False, "explanation_ar": "", "citation_indices": []})

    findings = scan_contract(contract_id=1, top_k=4)
    assert findings == []
