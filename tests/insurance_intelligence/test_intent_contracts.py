from __future__ import annotations

import pytest

from insurance_intelligence.contracts.intent import (
    IntentAnalyzerError,
    SUPPORTED_CONTRACT_VERSION,
    build_ambiguity,
    build_candidate_entity,
    build_follow_up,
    build_input,
    build_output,
)


def test_build_input_defaults():
    result = build_input(request_id="r1", text="What is a deductible?")
    assert result.contract_version == SUPPORTED_CONTRACT_VERSION
    assert result.request_id == "r1"
    assert result.domain_hint == "unknown"
    assert result.language == "en"
    assert result.conversation_context == ()
    assert result.known_entity_mentions == ()


def test_build_input_rejects_wrong_contract_version():
    with pytest.raises(IntentAnalyzerError, match="contract_version"):
        build_input(request_id="r1", text="hello", contract_version="2.0")


def test_build_input_rejects_empty_request_id():
    with pytest.raises(IntentAnalyzerError, match="request_id"):
        build_input(request_id="", text="hello")


def test_build_input_rejects_invalid_domain_hint():
    with pytest.raises(IntentAnalyzerError, match="domain_hint"):
        build_input(request_id="r1", text="hello", domain_hint="crypto")


def test_build_input_rejects_invalid_language():
    with pytest.raises(IntentAnalyzerError, match="language"):
        build_input(request_id="r1", text="hello", language="fr")


def test_build_input_validates_conversation_context():
    result = build_input(
        request_id="r1",
        text="hello",
        conversation_context=[{"role": "user", "text": "hi", "sequence": 1}],
    )
    assert len(result.conversation_context) == 1
    assert result.conversation_context[0].role == "user"


def test_build_input_rejects_invalid_conversation_role():
    with pytest.raises(IntentAnalyzerError, match="role"):
        build_input(
            request_id="r1",
            text="hello",
            conversation_context=[{"role": "assistant", "text": "hi", "sequence": 1}],
        )


def test_build_output_requires_governed_primary_intent():
    with pytest.raises(Exception):
        build_output(
            request_id="r1",
            primary_intent="NOT_A_REAL_INTENT",
            domain="health",
            requested_outcome="x",
            confidence=0.5,
            analysis_status="CLASSIFIED",
        )


def test_build_output_rejects_primary_duplicated_in_secondary():
    with pytest.raises(IntentAnalyzerError, match="duplicated"):
        build_output(
            request_id="r1",
            primary_intent="TERM_EXPLANATION",
            secondary_intents=["TERM_EXPLANATION"],
            domain="health",
            requested_outcome="x",
            confidence=0.5,
            analysis_status="CLASSIFIED",
        )


def test_build_output_rejects_duplicate_secondary_intents():
    with pytest.raises(IntentAnalyzerError, match="unique"):
        build_output(
            request_id="r1",
            primary_intent="TERM_EXPLANATION",
            secondary_intents=["CALCULATION", "CALCULATION"],
            domain="health",
            requested_outcome="x",
            confidence=0.5,
            analysis_status="CLASSIFIED",
        )


def test_build_output_rejects_confidence_out_of_bounds():
    with pytest.raises(IntentAnalyzerError, match="confidence"):
        build_output(
            request_id="r1",
            primary_intent="TERM_EXPLANATION",
            domain="health",
            requested_outcome="x",
            confidence=1.5,
            analysis_status="CLASSIFIED",
        )


def test_build_output_requires_clarification_question_when_status_requires_it():
    with pytest.raises(IntentAnalyzerError, match="clarification_question"):
        build_output(
            request_id="r1",
            primary_intent="FOLLOW_UP",
            domain="health",
            requested_outcome="x",
            confidence=0.3,
            analysis_status="CLARIFICATION_REQUIRED",
        )


def test_build_output_rejects_clarification_question_when_not_required():
    with pytest.raises(IntentAnalyzerError, match="clarification_question"):
        build_output(
            request_id="r1",
            primary_intent="TERM_EXPLANATION",
            domain="health",
            requested_outcome="x",
            confidence=0.9,
            analysis_status="CLASSIFIED",
            clarification_question="Which one?",
        )


def test_build_output_accepts_valid_clarification():
    result = build_output(
        request_id="r1",
        primary_intent="FOLLOW_UP",
        domain="health",
        requested_outcome="x",
        confidence=0.3,
        analysis_status="CLARIFICATION_REQUIRED",
        clarification_question="Which plan do you mean?",
    )
    assert result.clarification_question == "Which plan do you mean?"


def test_build_candidate_entity_rejects_invalid_type():
    with pytest.raises(IntentAnalyzerError):
        build_candidate_entity(
            entity_type="NOT_A_TYPE", surface_text="x", normalized_text="x", source="pattern", confidence=0.5
        )


def test_build_ambiguity_rejects_invalid_materiality():
    with pytest.raises(IntentAnalyzerError):
        build_ambiguity(ambiguity_type="MISSING_SUBJECT", description="x", materiality="extreme")


def test_build_follow_up_default_is_not_follow_up():
    result = build_follow_up(is_follow_up=False)
    assert result.reference_type == "none"
    assert result.confidence == 0.0
