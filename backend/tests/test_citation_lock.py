"""Direct unit coverage for the shared citation-lock primitives (used by both
qa.py and risk/scanner.py) that isn't already exercised indirectly through
test_qa.py - parse_json_object's own contract, and resolve_citations called
in isolation."""

import pytest

from app.rag.citation_lock import parse_json_object, resolve_citations
from app.rag.retrieval import EvidenceChunk

EVIDENCE = [
    EvidenceChunk(
        chunk_id="1:0",
        text="Clause A text.",
        similarity=0.9,
        filename="a.pdf",
        clause_number="1",
        clause_title="A",
        page_number=1,
    ),
    EvidenceChunk(
        chunk_id="1:1",
        text="Clause B text.",
        similarity=0.6,
        filename="a.pdf",
        clause_number="2",
        clause_title="B",
        page_number=2,
    ),
]


@pytest.mark.parametrize(
    "raw",
    ["not json at all", "[1, 2, 3]", '"a bare string"', "42", "null", ""],
)
def test_parse_json_object_returns_none_for_non_object_input(raw):
    assert parse_json_object(raw) is None


def test_parse_json_object_returns_dict_for_valid_object():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_resolve_citations_empty_list_returns_empty():
    citations, similarities = resolve_citations([], EVIDENCE)
    assert citations == []
    assert similarities == []


def test_resolve_citations_non_list_input_returns_empty():
    citations, similarities = resolve_citations("1", EVIDENCE)
    assert citations == []
    assert similarities == []


def test_resolve_citations_valid_indices_preserve_order_given():
    citations, similarities = resolve_citations([2, 1], EVIDENCE)
    assert [c.clause_number for c in citations] == ["2", "1"]
    assert similarities == [0.6, 0.9]
