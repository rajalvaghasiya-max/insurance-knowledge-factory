from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.education_publication.repository import EducationPublicationRepository
from insurance_intelligence.llm.provider import DeterministicFakeTextProvider
from policy_scna_app.health_customer_v0 import (
    HealthCustomerRelevanceError,
    ask_health_question,
    enforce_relevance,
)

ROOT = Path(__file__).resolve().parents[2]
PED_EDUCATION = (
    ROOT
    / "knowledge/factory/education_publications"
    / "pre_existing_disease_education_publication.json"
)


def _resolved_output(concept_id: str, *, semantic_fact: str = "definition") -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.99,
            "primary_intent": "understand_policy_term",
            "requested_outcome": "POLICY_FACT_EXPLANATION",
            "governed_concept_candidates": [
                {"concept_id": concept_id, "confidence": 0.99}
            ],
            "selected_concept_id": concept_id,
            "requested_semantic_fact": semantic_fact,
            "scenario_facts": [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        },
        sort_keys=True,
    )


def _ped_only_repository() -> EducationPublicationRepository:
    return EducationPublicationRepository.from_json_files((PED_EDUCATION,))


def test_ped_question_releases_only_ped_customer_education() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output("health:concept:pre_existing_disease")
    )

    result = ask_health_question(
        question="I had a thyroid problem before I bought health insurance. What does pre-existing disease mean for me?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-ped-test",
        execution_id="health-v0-ped-test-execution",
        created_at="2026-10-18T06:00:00Z",
        education_repository=_ped_only_repository(),
    )

    assert result.status == "ANSWER"
    assert result.selected_concept_id == "health:concept:pre_existing_disease"
    assert result.selected_topic == "pre_existing_disease"
    assert result.render_outcome == "PASS"
    lowered = result.released_text.casefold()
    assert "pre-existing disease" in lowered
    assert "co-payment" not in lowered
    assert "claim will be approved" not in lowered
    assert "insurer will pay" not in lowered


def test_missing_education_fails_closed_without_substituting_another_concept() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output("health:concept:bariatric_surgery")
    )

    result = ask_health_question(
        question="Is weight-loss surgery treated as cosmetic, or can health insurance cover it?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-bariatric-test",
        execution_id="health-v0-bariatric-test-execution",
        created_at="2026-10-18T06:00:00Z",
        education_repository=_ped_only_repository(),
    )

    assert result.status == "CLARIFICATION"
    assert result.selected_concept_id == "health:concept:bariatric_surgery"
    assert result.selected_topic == "bariatric_surgery"
    assert result.render_outcome == "PASS"
    lowered = result.released_text.casefold()
    assert "bariatric surgery" in lowered
    assert "do not yet have an approved customer explanation" in lowered
    assert "pre-existing disease" not in lowered
    assert "co-payment" not in lowered


def test_relevance_invariant_rejects_wrong_concept_before_release() -> None:
    with pytest.raises(HealthCustomerRelevanceError):
        enforce_relevance(
            asked_concept_id="health:concept:bariatric_surgery",
            answer_topic="conditional_copayment",
        )


def test_relevance_invariant_accepts_governed_downstream_topic() -> None:
    enforce_relevance(
        asked_concept_id="health:concept:room_rent_limit",
        answer_topic="room_rent_limit",
    )
