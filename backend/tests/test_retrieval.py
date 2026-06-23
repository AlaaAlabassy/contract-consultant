"""Edge cases for app/rag/retrieval.py: missing/partial chunk metadata must
not crash the mapping into EvidenceChunk, since older or malformed Chroma
records may lack clause_number/page_number."""

from dataclasses import dataclass

from app.rag import retrieval


@dataclass
class _FakeRawChunk:
    chunk_id: str
    text: str
    similarity: float
    metadata: dict


def test_empty_results_returns_empty_list(monkeypatch):
    monkeypatch.setattr(retrieval, "embed_query", lambda q: [0.1, 0.2])
    monkeypatch.setattr(retrieval.chroma_store, "query", lambda *a, **k: [])
    result = retrieval.retrieve("سؤال")
    assert result == []


def test_missing_metadata_fields_default_safely(monkeypatch):
    monkeypatch.setattr(retrieval, "embed_query", lambda q: [0.1, 0.2])
    raw = [_FakeRawChunk(chunk_id="1:0", text="some clause text", similarity=0.8, metadata={})]
    monkeypatch.setattr(retrieval.chroma_store, "query", lambda *a, **k: raw)

    [chunk] = retrieval.retrieve("سؤال")

    assert chunk.filename == ""
    assert chunk.clause_number == ""
    assert chunk.clause_title == ""
    assert chunk.page_number is None


def test_contract_id_and_top_k_are_forwarded_to_chroma_query(monkeypatch):
    monkeypatch.setattr(retrieval, "embed_query", lambda q: [0.1, 0.2])
    captured = {}

    def fake_query(embedding, top_k=8, contract_id=None):
        captured["embedding"] = embedding
        captured["top_k"] = top_k
        captured["contract_id"] = contract_id
        return []

    monkeypatch.setattr(retrieval.chroma_store, "query", fake_query)
    retrieval.retrieve("سؤال", top_k=3, contract_id=42)

    assert captured == {"embedding": [0.1, 0.2], "top_k": 3, "contract_id": 42}
