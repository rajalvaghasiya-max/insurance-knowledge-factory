from __future__ import annotations

from pathlib import Path

import pytest

from insurance_intelligence.contracts.request_authority import (
    RequestAuthorityError,
    build_input,
    build_output,
)
from insurance_intelligence.request_authority import classify_request_authority


@pytest.mark.parametrize(
    "text",
    [
        "What is a co-pay?",
        "Explain my waiting period.",
        "Compare these two policies.",
        "How much is the deductible?",
    ],
)
def test_assertive_requests_are_routed_to_standard_grounding(text: str) -> None:
    result = classify_request_authority(build_input(request_id="req-a", text=text))
    assert result.authority_class == "ASSERTIVE"
    assert result.downstream_guard == "STANDARD_ASSERTION_GROUNDING"
    assert result.intent_analysis_authorized is True
    assert result.recommendation_authorized is False
    assert result.matched_assertive_cues
    assert result.matched_advisory_cues == ()


@pytest.mark.parametrize(
    "text",
    [
        "Should I increase my base cover or buy a super top-up?",
        "Which plan is better for me?",
        "Can you recommend a policy?",
        "Do I need a higher sum insured?",
    ],
)
def test_advisory_requests_raise_context_and_safety_obligation(text: str) -> None:
    result = classify_request_authority(build_input(request_id="req-b", text=text))
    assert result.authority_class == "ADVISORY"
    assert result.downstream_guard == "ADVISORY_CONTEXT_AND_SAFETY_REQUIRED"
    assert result.intent_analysis_authorized is True
    assert result.recommendation_authorized is False
    assert result.matched_advisory_cues
    assert result.matched_assertive_cues == ()


def test_mixed_request_cannot_hide_advisory_part_behind_fact_question() -> None:
    result = classify_request_authority(
        build_input(
            request_id="req-mixed",
            text="Explain the deductible and tell me which plan is better for me.",
        )
    )
    assert result.authority_class == "MIXED"
    assert result.downstream_guard == (
        "SPLIT_ASSERTIVE_AND_ADVISORY_WITH_ADVISORY_SAFETY_REQUIRED"
    )
    assert result.matched_assertive_cues
    assert result.matched_advisory_cues
    assert result.recommendation_authorized is False


def test_unresolved_request_fails_closed_instead_of_defaulting_assertive() -> None:
    result = classify_request_authority(
        build_input(request_id="req-u", text="And this one?")
    )
    assert result.authority_class == "UNRESOLVED"
    assert result.downstream_guard == "CLARIFY_REQUESTED_AUTHORITY"
    assert result.intent_analysis_authorized is False
    assert result.recommendation_authorized is False
    assert result.matched_assertive_cues == ()
    assert result.matched_advisory_cues == ()


def test_boundary_rejects_empty_request_text() -> None:
    with pytest.raises(RequestAuthorityError):
        build_input(request_id="req-empty", text="   ")


def test_contract_never_allows_recommendation_authorization() -> None:
    with pytest.raises(RequestAuthorityError):
        build_output(
            request_id="req-x",
            authority_class="ADVISORY",
            matched_advisory_cues=("recommend",),
            classification_basis="matched_advisory_cues",
            downstream_guard="ADVISORY_CONTEXT_AND_SAFETY_REQUIRED",
            intent_analysis_authorized=True,
            recommendation_authorized=True,
        )


def test_unresolved_contract_cannot_authorize_intent_analysis() -> None:
    with pytest.raises(RequestAuthorityError):
        build_output(
            request_id="req-x",
            authority_class="UNRESOLVED",
            classification_basis="no_governed_authority_cue_matched",
            downstream_guard="CLARIFY_REQUESTED_AUTHORITY",
            intent_analysis_authorized=True,
        )


def test_boundary_has_no_knowledge_factory_or_domain_imports() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / "insurance_intelligence/request_authority.py").read_text(
        encoding="utf-8"
    )
    assert "factory_core" not in source
    assert "knowledge_domains" not in source
    assert "requests" not in source
    assert "openai" not in source.lower()


def test_request_authority_registries_are_immutable_tuples() -> None:
    from insurance_intelligence.request_authority import ADVISORY_CUES, ASSERTIVE_CUES

    assert isinstance(ASSERTIVE_CUES, tuple)
    assert isinstance(ADVISORY_CUES, tuple)
    assert ASSERTIVE_CUES
    assert ADVISORY_CUES
