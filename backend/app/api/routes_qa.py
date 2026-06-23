from __future__ import annotations

import json
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from app.db.models import ChatMessage
from app.db.session import SessionLocal
from app.rag.qa import answer_question

router = APIRouter(prefix="/api/qa", tags=["qa"])


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    contract_id: int | None = None


class CitationOut(BaseModel):
    clause_number: str
    page_number: int | None
    filename: str
    quote_en: str


class AskResponse(BaseModel):
    conversation_id: str
    answer_ar: str
    confidence: float
    confidence_label: str
    citations: list[CitationOut]


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    conversation_id = req.conversation_id or str(uuid.uuid4())
    result = answer_question(req.question, contract_id=req.contract_id)

    db = SessionLocal()
    try:
        db.add(
            ChatMessage(
                conversation_id=conversation_id,
                question_ar=req.question,
                answer_ar=result.answer_ar,
                confidence=result.confidence,
                confidence_label=result.confidence_label,
                citations_json=json.dumps([c.__dict__ for c in result.citations], ensure_ascii=False),
            )
        )
        db.commit()
    finally:
        db.close()

    return AskResponse(
        conversation_id=conversation_id,
        answer_ar=result.answer_ar,
        confidence=result.confidence,
        confidence_label=result.confidence_label,
        citations=[CitationOut(**c.__dict__) for c in result.citations],
    )
