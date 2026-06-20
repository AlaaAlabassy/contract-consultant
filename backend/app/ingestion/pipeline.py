"""Orchestrates: list Drive files -> parse -> clause-split -> embed -> store
in Chroma + Postgres -> update the Contract registry.

Re-running ingestion on an unchanged file (same drive_modified_time) is a
no-op, so this can be re-run freely (e.g. on a schedule, or manually via the
CLI) without re-embedding everything each time.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.chunking.clause_splitter import split_into_clauses
from app.db.models import Clause, Contract
from app.db.session import SessionLocal
from app.drive import client as drive_client
from app.embeddings.embedder import embed_passages
from app.parsing.docx_parser import parse_docx_pages
from app.parsing.gdoc_parser import parse_gdoc_pages
from app.parsing.pdf_parser import parse_pdf_pages
from app.vectorstore import chroma_store

logger = logging.getLogger(__name__)

PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GDOC_MIME = "application/vnd.google-apps.document"

SUPPORTED_MIME_TYPES = {PDF_MIME, DOCX_MIME, GDOC_MIME}


def run_ingestion(folder_id: str) -> dict:
    """Ingests every supported file under `folder_id` (recursively).
    Returns a summary dict: {"ingested": [...], "skipped": [...], "failed": [...]}."""
    summary = {"ingested": [], "skipped": [], "failed": []}

    files = drive_client.list_files(folder_id, recursive=True)
    db = SessionLocal()
    try:
        for f in files:
            if f["mimeType"] not in SUPPORTED_MIME_TYPES:
                summary["skipped"].append({"name": f["name"], "reason": "unsupported mime type"})
                continue
            try:
                changed = _ingest_one_file(db, f)
                key = "ingested" if changed else "skipped"
                summary[key].append({"name": f["name"]})
            except Exception as exc:  # noqa: BLE001 - keep going across the whole batch
                logger.exception("Failed to ingest %s", f["name"])
                summary["failed"].append({"name": f["name"], "reason": str(exc)})
        db.commit()
    finally:
        db.close()

    return summary


def _ingest_one_file(db: Session, file_meta: dict) -> bool:
    modified_time = _parse_drive_time(file_meta["modifiedTime"])
    contract = db.query(Contract).filter_by(drive_file_id=file_meta["id"]).first()

    if contract and contract.drive_modified_time and contract.drive_modified_time >= modified_time:
        return False  # unchanged since last ingestion

    pages = _parse_pages(file_meta)
    chunks = split_into_clauses(pages)
    if not chunks:
        logger.warning("No chunks extracted from %s", file_meta["name"])
        return False

    if contract is None:
        contract = Contract(
            drive_file_id=file_meta["id"],
            filename=file_meta["name"],
            mime_type=file_meta["mimeType"],
        )
        db.add(contract)
        db.flush()  # assign contract.id
    else:
        contract.filename = file_meta["name"]
        chroma_store.delete_by_contract(contract.id)
        db.query(Clause).filter_by(contract_id=contract.id).delete()

    contract.page_count = max((p for p, _ in pages), default=1)
    contract.drive_modified_time = modified_time
    contract.last_ingested_at = datetime.now(timezone.utc)

    embeddings = embed_passages([c.raw_text for c in chunks])

    chunk_ids, metadatas = [], []
    for i, chunk in enumerate(chunks):
        chunk_id = f"{contract.id}:{i}"
        chunk_ids.append(chunk_id)
        metadatas.append(
            {
                "contract_id": contract.id,
                "filename": contract.filename,
                "clause_number": chunk.clause_number or "",
                "clause_title": chunk.clause_title or "",
                "page_number": chunk.page_number,
            }
        )
        db.add(
            Clause(
                contract_id=contract.id,
                clause_number=chunk.clause_number,
                clause_title=chunk.clause_title,
                page_number=chunk.page_number,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                raw_text=chunk.raw_text,
                chroma_chunk_id=chunk_id,
            )
        )

    chroma_store.add_chunks(
        chunk_ids=chunk_ids,
        texts=[c.raw_text for c in chunks],
        embeddings=embeddings,
        metadatas=metadatas,
    )

    db.flush()
    return True


def _parse_pages(file_meta: dict) -> list[tuple[int, str]]:
    mime = file_meta["mimeType"]
    if mime == PDF_MIME:
        return parse_pdf_pages(drive_client.download_file(file_meta["id"]))
    if mime == DOCX_MIME:
        return parse_docx_pages(drive_client.download_file(file_meta["id"]))
    if mime == GDOC_MIME:
        return parse_gdoc_pages(drive_client.export_gdoc(file_meta["id"]))
    raise ValueError(f"Unsupported mime type: {mime}")


def _parse_drive_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
