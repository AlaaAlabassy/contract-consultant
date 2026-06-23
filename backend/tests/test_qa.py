"""Edge-case coverage for citation-lock answering (app/rag/qa.py).

The core guarantee under test: the system must collapse to a refusal
whenever it cannot point to verifiable evidence, and must never let the LLM
supply citation text directly - only an index into the retrieved chunks,
resolved server-side to the literal chunk text.
"""

import json

import pytest

from app.rag import qa
from app.rag.qa import REFUSAL_TEXT_AR, answer_question
from app.rag.retrieval import EvidenceChunk

EVIDENCE = [
    EvidenceChunk(
        chunk_id="1:0",
        text="The Contractor shall submit an Advance Payment Guarantee.",
        similarity=0.95,
        filename="contract.pdf",
        clause_number="14.2",
        clause_title="Advance Payment",
        page_number=12,
    ),
    EvidenceChunk(
        chunk_id="1:1",
        text="The Employer shall pay within 56 days of certification.",
        similarity=0.72,
        filename="contract.pdf",
        clause_number="14.7",
        clause_title="Payment",
        page_number=14,
    ),
]


def _stub_llm(monkeypatch, response_obj=None, raise_exc=None, raw_text=None):
    def fake_chat_completion(messages):
        if raise_exc:
            raise raise_exc
        if raw_text is not None:
            return raw_text
        return json.dumps(response_obj)

    monkeypatch.setattr(qa, "chat_completion", fake_chat_completion)


def _stub_retrieval(monkeypatch, evidence=EVIDENCE):
    monkeypatch.setattr(qa, "retrieve", lambda question, top_k=8, contract_id=None: evidence)


def test_no_evidence_returns_refusal(monkeypatch):
    _stub_retrieval(monkeypatch, evidence=[])
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"
    assert result.answer_ar == REFUSAL_TEXT_AR
    assert result.citations == []


def test_llm_exception_returns_refusal(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, raise_exc=RuntimeError("network error"))
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"


def test_malformed_json_returns_refusal(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, raw_text="this is not json")
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"


def test_unsupported_flag_returns_refusal_even_with_citations(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": False, "answer_ar": "إجابة مفترضة", "citation_indices": [1]},
    )
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"
    assert result.answer_ar == REFUSAL_TEXT_AR


def test_empty_citation_indices_returns_refusal(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": []},
    )
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"


@pytest.mark.parametrize("bad_indices", [[0], [99], ["1"], [None], [1.5]])
def test_out_of_range_or_wrong_type_indices_are_dropped(monkeypatch, bad_indices):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": bad_indices},
    )
    result = answer_question("ما هي مدة الدفع؟")
    assert result.confidence_label == "refuse"
    assert result.citations == []


def test_valid_index_resolves_to_literal_chunk_text_not_llm_text(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={
            "supported": True,
            "answer_ar": "  يجب على المتعاقد تقديم ضمان دفعة مقدمة.  ",
            "citation_indices": [1],
            # An attacker/hallucinating model might add extra fields - they must be ignored.
            "citations": [{"quote_en": "fabricated quote not in the contract"}],
        },
    )
    result = answer_question("ما هو شرط الدفعة المقدمة؟")
    assert result.answer_ar == "يجب على المتعاقد تقديم ضمان دفعة مقدمة."  # stripped
    assert len(result.citations) == 1
    assert result.citations[0].quote_en == EVIDENCE[0].text
    assert result.citations[0].clause_number == "14.2"
    assert result.citations[0].page_number == 12


def test_partial_invalid_indices_keep_only_valid_ones(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [1, 99, 0]},
    )
    result = answer_question("سؤال")
    assert len(result.citations) == 1
    assert result.citations[0].clause_number == "14.2"
    assert result.confidence == EVIDENCE[0].similarity


def test_confidence_is_minimum_across_cited_chunks_not_average(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [1, 2]},
    )
    result = answer_question("سؤال")
    assert result.confidence == min(EVIDENCE[0].similarity, EVIDENCE[1].similarity)


@pytest.mark.parametrize(
    "confidence,expected_label",
    [
        (0.95, "high"),
        (0.90, "high"),
        (0.89999, "warn"),
        (0.70, "warn"),
        (0.69999, "red"),
        (0.50, "red"),
        (0.49999, "refuse"),
        (0.0, "refuse"),
    ],
)
def test_confidence_label_boundaries(confidence, expected_label):
    assert qa._label(confidence) == expected_label


# --- Queries with no real match in the data (low-similarity retrieval) ------

LOW_SIMILARITY_EVIDENCE = [
    EvidenceChunk(
        chunk_id="1:0",
        text="An unrelated clause about insurance.",
        similarity=0.18,
        filename="contract.pdf",
        clause_number="19.1",
        clause_title="Insurance",
        page_number=30,
    )
]


def test_low_similarity_evidence_still_resolves_below_refuse_threshold(monkeypatch):
    """Even if the LLM (wrongly) claims support off weak evidence, the
    similarity-derived confidence must still gate it down to a refusal -
    confidence is never trusted from the LLM's own say-so."""
    _stub_retrieval(monkeypatch, evidence=LOW_SIMILARITY_EVIDENCE)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة غير موثوقة", "citation_indices": [1]},
    )
    result = answer_question("سؤال لا علاقة له بمحتوى العقد")
    assert result.confidence_label == "refuse"
    assert result.confidence == pytest.approx(0.18)


# --- Ambiguous / malformed LLM output ---------------------------------------


def test_markdown_fenced_json_is_parsed_not_refused(monkeypatch):
    """anthropic/claude-sonnet-4.6 via OpenRouter wraps its JSON in a ```json
    fence even with response_format=json_object (confirmed in live testing), so
    the fence must be stripped and the answer honored - not thrown away. The
    citation-lock guarantee is unaffected: the quote still comes from evidence."""
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        raw_text='```json\n{"supported": true, "answer_ar": "إجابة", "citation_indices": [1]}\n```',
    )
    result = answer_question("سؤال")
    assert result.confidence_label != "refuse"
    assert result.answer_ar == "إجابة"
    assert result.citations[0].quote_en == EVIDENCE[0].text


def test_json_with_surrounding_prose_is_extracted(monkeypatch):
    """Some responses prepend prose before the JSON object; the first {...}
    span should still be extracted rather than degrading to a refusal."""
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        raw_text='Here is my answer:\n{"supported": true, "answer_ar": "إجابة", "citation_indices": [1]}',
    )
    result = answer_question("سؤال")
    assert result.confidence_label != "refuse"
    assert result.answer_ar == "إجابة"


def test_json_top_level_array_is_treated_as_malformed(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, raw_text="[1, 2, 3]")
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_json_top_level_string_is_treated_as_malformed(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(monkeypatch, raw_text='"إجابة حرة بدون بنية"')
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_null_citation_indices_does_not_crash(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": None},
    )
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_citation_indices_as_scalar_instead_of_list_is_rejected(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": 1},
    )
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_null_answer_ar_with_valid_citation_does_not_crash(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": None, "citation_indices": [1]},
    )
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_blank_answer_ar_with_valid_citation_is_refused(monkeypatch):
    """A 'supported' response with only whitespace as the answer is
    degenerate output, not a usable answer - must not be shown to the user."""
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "   ", "citation_indices": [1]},
    )
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


def test_bool_true_is_not_accepted_as_citation_index(monkeypatch):
    """Python bool is a subclass of int, so True == 1 - this must not let a
    type-confused index silently resolve to evidence[0]."""
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [True]},
    )
    result = answer_question("سؤال")
    assert result.confidence_label == "refuse"


# --- citation_indices <-> evidence matching ---------------------------------


def test_duplicate_indices_are_deduplicated(monkeypatch):
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [1, 1, 1]},
    )
    result = answer_question("سؤال")
    assert len(result.citations) == 1
    assert result.citations[0].clause_number == "14.2"


def test_each_citation_maps_to_its_own_distinct_evidence_chunk(monkeypatch):
    """With two distinct cited indices, every returned Citation must match
    the exact evidence chunk at that index - not get mixed up or collapsed."""
    _stub_retrieval(monkeypatch)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [2, 1]},
    )
    result = answer_question("سؤال")
    assert len(result.citations) == 2
    by_clause = {c.clause_number: c for c in result.citations}
    assert by_clause["14.2"].quote_en == EVIDENCE[0].text
    assert by_clause["14.2"].page_number == 12
    assert by_clause["14.7"].quote_en == EVIDENCE[1].text
    assert by_clause["14.7"].page_number == 14


def test_same_clause_number_from_different_files_resolved_by_index_not_text(monkeypatch):
    """Cross-document corpora can have two contracts that both use FIDIC
    clause numbering (e.g. two '14.2' clauses from different files). Citation
    resolution must key off the evidence index, not clause_number text, or
    these would be ambiguous."""
    ambiguous_evidence = [
        EvidenceChunk(
            chunk_id="1:0",
            text="Contract A's advance payment clause.",
            similarity=0.91,
            filename="contract_a.pdf",
            clause_number="14.2",
            clause_title="Advance Payment",
            page_number=12,
        ),
        EvidenceChunk(
            chunk_id="2:0",
            text="Contract B's advance payment clause.",
            similarity=0.88,
            filename="contract_b.pdf",
            clause_number="14.2",
            clause_title="Advance Payment",
            page_number=9,
        ),
    ]
    _stub_retrieval(monkeypatch, evidence=ambiguous_evidence)
    _stub_llm(
        monkeypatch,
        response_obj={"supported": True, "answer_ar": "إجابة", "citation_indices": [2]},
    )
    result = answer_question("سؤال")
    assert len(result.citations) == 1
    assert result.citations[0].filename == "contract_b.pdf"
    assert result.citations[0].quote_en == "Contract B's advance payment clause."
