from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    drive_file_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    filename: Mapped[str] = mapped_column(String(512))
    contract_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(128))
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    drive_modified_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    clauses: Mapped[list["Clause"]] = relationship(back_populates="contract", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    clause_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    clause_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    chroma_chunk_id: Mapped[str] = mapped_column(String(128), unique=True)

    contract: Mapped["Contract"] = relationship(back_populates="clauses")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(64), index=True)
    question_ar: Mapped[str] = mapped_column(Text)
    answer_ar: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    confidence_label: Mapped[str] = mapped_column(String(16))
    citations_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskResult(Base):
    __tablename__ = "risk_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    rule_key: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16))
    explanation_ar: Mapped[str] = mapped_column(Text)
    clause_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CompareResult(Base):
    __tablename__ = "compare_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    clause_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
