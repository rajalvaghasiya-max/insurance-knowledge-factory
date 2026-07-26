from __future__ import annotations

import pytest

from insurance_intelligence.contracts.context import (
    ContextBuilderError,
    build_assumption,
    build_context_conflict,
    build_document_context_item,
    build_input,
    build_missing_context_item,
    build_output,
    build_resolved_context_item,
    build_user_context_item,
)
from insurance_intelligence.contracts.intent import build_input as build_intent_input, build_output as build_intent_output
from insurance_intelligence.intent.analyzer import IntentAnalyzer


def _sample_intent_analysis():
    return IntentAnalyzer().analyze(build_intent_input(request_id="r1", text="What is a deductible?"))


def test_build_input_defaults():
    intent = _sample_intent_analysis()
    result = build_input(request_id="r1", intent_analysis=intent)
    assert result.contract_version == "1.0"
    assert result.user_context == ()
    assert result.conversation_context == ()
    assert result.document_context == ()
    assert result.session_context == ()


def test_build_input_rejects_wrong_contract_version():
    intent = _sample_intent_analysis()
    with pytest.raises(ContextBuilderError, match="contract_version"):
        build_input(request_id="r1", intent_analysis=intent, contract_version="9.9")


def test_build_input_requires_validated_intent_analysis():
    with pytest.raises(ContextBuilderError, match="intent_analysis"):
        build_input(request_id="r1", intent_analysis={"not": "valid"})  # type: ignore[arg-type]


def test_build_user_context_item():
    item = build_user_context_item({"key": "age", "value": "45", "source_reference": "turn1", "sequence": 1})
    assert item.key == "age"
    assert item.value == "45"


def test_build_document_context_item_validates_processing_status():
    with pytest.raises(ContextBuilderError):
        build_document_context_item(
            {"document_reference": "doc1", "document_type": "policy_wording", "processing_status": "WEIRD"}
        )


def test_build_resolved_context_item_validates_category_and_provenance():
    with pytest.raises(ContextBuilderError):
        build_resolved_context_item(
            key="age", value="45", category="NOT_A_CATEGORY", provenance="USER_PROVIDED",
            source_reference="x", confidence=0.9,
        )
    with pytest.raises(ContextBuilderError):
        build_resolved_context_item(
            key="age", value="45", category="USER", provenance="NOT_A_PROVENANCE",
            source_reference="x", confidence=0.9,
        )


def test_build_missing_context_item_requires_clarification_question():
    with pytest.raises(ContextBuilderError):
        build_missing_context_item(
            key="age", category="USER", required=True, materiality="high", reason="x", clarification_question=""
        )


def test_build_context_conflict_requires_two_values():
    with pytest.raises(ContextBuilderError):
        build_context_conflict(
            key="age", values=["45"], source_references=["x"], materiality="high", resolution_status="UNRESOLVED"
        )


def test_build_assumption_validates_materiality():
    with pytest.raises(ContextBuilderError):
        build_assumption(
            assumption_id="a1", key="deductible_type", value="annual", reason="default",
            materiality="extreme", user_visible=True, resolution_required=False,
        )


def test_build_output_requires_clarification_questions_when_required():
    with pytest.raises(ContextBuilderError, match="clarification_questions"):
        build_output(request_id="r1", answerability="CLARIFICATION_REQUIRED", context_completeness=0.3)


def test_build_output_rejects_clarification_questions_when_not_required():
    with pytest.raises(ContextBuilderError, match="clarification_questions"):
        build_output(
            request_id="r1", answerability="ANSWERABLE", context_completeness=1.0,
            clarification_questions=["Which one?"],
        )


def test_build_output_rejects_more_than_three_clarification_questions():
    with pytest.raises(ContextBuilderError, match="3"):
        build_output(
            request_id="r1", answerability="CLARIFICATION_REQUIRED", context_completeness=0.2,
            clarification_questions=["a?", "b?", "c?", "d?"],
        )


def test_build_output_rejects_completeness_out_of_bounds():
    with pytest.raises(ContextBuilderError, match="context_completeness"):
        build_output(request_id="r1", answerability="ANSWERABLE", context_completeness=1.5)


def test_build_output_rejects_invalid_answerability():
    with pytest.raises(ContextBuilderError):
        build_output(request_id="r1", answerability="MAYBE", context_completeness=0.5)


def test_build_output_accepts_valid_answerable():
    result = build_output(request_id="r1", answerability="ANSWERABLE", context_completeness=1.0)
    assert result.answerability == "ANSWERABLE"
    assert result.clarification_questions == ()
