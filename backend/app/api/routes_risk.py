from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.db.models import RiskResult
from app.db.session import SessionLocal
from app.risk.scanner import scan_contract

router = APIRouter(prefix="/api/risk", tags=["risk"])

# In-memory per-contract status, same rationale as routes_ingestion._state:
# single-process/solo-user v1 is enough; move to Redis if that changes.
_state: dict[int, dict] = {}


def _run_and_record(contract_id: int, top_k: int) -> None:
    _state[contract_id] = {"status": "running"}
    try:
        findings = scan_contract(contract_id, top_k=top_k)

        db = SessionLocal()
        try:
            db.query(RiskResult).filter_by(contract_id=contract_id).delete()
            for finding in findings:
                for citation in finding.citations:
                    db.add(
                        RiskResult(
                            contract_id=contract_id,
                            rule_key=finding.rule_key,
                            severity=finding.severity,
                            explanation_ar=finding.explanation_ar,
                            clause_number=citation.clause_number,
                            page_number=citation.page_number,
                            confidence=finding.confidence,
                        )
                    )
            db.commit()
        finally:
            db.close()

        _state[contract_id] = {"status": "done", "findings_count": len(findings)}
    except Exception as exc:  # noqa: BLE001
        _state[contract_id] = {"status": "error", "error": str(exc)}


class ScanRequest(BaseModel):
    contract_id: int
    top_k: int = 4


@router.post("/scan")
def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_and_record, req.contract_id, req.top_k)
    return {"status": "started", "contract_id": req.contract_id}


@router.get("/scan/status")
def scan_status(contract_id: int) -> dict:
    return _state.get(contract_id, {"status": "idle"})


class RiskResultOut(BaseModel):
    rule_key: str
    severity: str
    explanation_ar: str
    clause_number: str | None
    page_number: int | None
    confidence: float


@router.get("/{contract_id}")
def get_risk_results(contract_id: int) -> list[RiskResultOut]:
    db = SessionLocal()
    try:
        rows = db.query(RiskResult).filter_by(contract_id=contract_id).all()
        return [
            RiskResultOut(
                rule_key=row.rule_key,
                severity=row.severity,
                explanation_ar=row.explanation_ar,
                clause_number=row.clause_number,
                page_number=row.page_number,
                confidence=row.confidence,
            )
            for row in rows
        ]
    finally:
        db.close()
