from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.models import Contract
from app.db.session import SessionLocal

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


class ContractOut(BaseModel):
    id: int
    filename: str
    contract_type: str | None
    page_count: int | None
    last_ingested_at: str | None


@router.get("")
def list_contracts() -> list[ContractOut]:
    """List ingested contracts so clients (e.g. the risk dashboard) can pick a
    contract_id without guessing. Read-only, ordered by filename."""
    db = SessionLocal()
    try:
        rows = db.query(Contract).order_by(Contract.filename).all()
        return [
            ContractOut(
                id=row.id,
                filename=row.filename,
                contract_type=row.contract_type,
                page_count=row.page_count,
                last_ingested_at=row.last_ingested_at.isoformat() if row.last_ingested_at else None,
            )
            for row in rows
        ]
    finally:
        db.close()
