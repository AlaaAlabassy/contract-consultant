from __future__ import annotations

from dataclasses import dataclass

from app.embeddings.embedder import embed_query
from app.vectorstore import chroma_store


@dataclass
class EvidenceChunk:
    chunk_id: str
    text: str
    similarity: float
    filename: str
    clause_number: str
    clause_title: str
    page_number: int | None


def retrieve(question: str, top_k: int = 8, contract_id: int | None = None) -> list[EvidenceChunk]:
    embedding = embed_query(question)
    raw = chroma_store.query(embedding, top_k=top_k, contract_id=contract_id)
    return [
        EvidenceChunk(
            chunk_id=c.chunk_id,
            text=c.text,
            similarity=c.similarity,
            filename=c.metadata.get("filename", ""),
            clause_number=c.metadata.get("clause_number") or "",
            clause_title=c.metadata.get("clause_title") or "",
            page_number=c.metadata.get("page_number"),
        )
        for c in raw
    ]
