"""Wraps the ChromaDB server container (chromadb service in docker-compose)
as a single "contract_clauses" collection holding chunks from every ingested
contract. Cross-document Smart Search (Phase 4) relies on this being one
shared collection rather than one-per-contract, so retrieval can run across
the whole corpus without a contract filter.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import chromadb

from app.config import settings

COLLECTION_NAME = "contract_clauses"


@lru_cache(maxsize=1)
def _client() -> chromadb.ClientAPI:
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def _collection():
    return _client().get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    similarity: float
    metadata: dict


def add_chunks(
    chunk_ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> None:
    if not chunk_ids:
        return
    _collection().upsert(ids=chunk_ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def delete_by_contract(contract_id: int) -> None:
    _collection().delete(where={"contract_id": contract_id})


def query(
    query_embedding: list[float], top_k: int = 8, contract_id: int | None = None
) -> list[RetrievedChunk]:
    where = {"contract_id": contract_id} if contract_id is not None else None
    result = _collection().query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[RetrievedChunk] = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    for chunk_id, doc, meta, dist in zip(ids, docs, metas, dists):
        # Collection uses cosine space, so distance = 1 - cosine_similarity.
        similarity = 1 - dist
        chunks.append(RetrievedChunk(chunk_id=chunk_id, text=doc, similarity=similarity, metadata=meta))

    return chunks
