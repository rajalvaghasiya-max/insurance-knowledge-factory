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


def _resolved_output(
    concept_id: str,
    *,
    semantic_fact: str = "definition",
    requested_outcome: str = "POLICY_FACT_EXPLANATION",
    scenario_facts: list[dict[str, str]] | None = None,
) -> str:
    return json.dumps(
        {
            "interpretation_status": "RESOLVED",
            "confidence": 0.99,
            "primary_intent": "understand_policy_term",
            "requested_outcome": requested_outcome,
            "governed_concept_candidates": [
                {"concept_id": concept_id, "confidence": 0.99}
            ],
            "selected_concept_id": concept_id,
            "requested_semantic_fact": semantic_fact,
            "scenario_facts": scenario_facts or [],
            "request_authority_class": "ASSERTIVE",
            "ambiguity_reasons": [],
            "competing_interpretations": [],
        },
        sort_keys=True,
    )


def _ped_only_repository() -> EducationPublicationRepository:
    return EducationPublicationRepository.from_json_files((PED_EDUCATION,))


def _ask_ped(*, semantic_fact: str, requested_outcome: str = "POLICY_FACT_EXPLANATION"):
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            semantic_fact=semantic_fact,
            requested_outcome=requested_outcome,
        )
    )
    return ask_health_question(
        question="Explain the relevant PED point.",
        provider=provider,
        model_name="test-model",
        request_id=f"health-v0-ped-{semantic_fact}-{requested_outcome}",
        execution_id=f"health-v0-ped-{semantic_fact}-{requested_outcome}-execution",
        created_at="2026-10-18T06:00:00Z",
        education_repository=_ped_only_repository(),
    )


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


def test_definition_projection_does_not_dump_unrequested_example_or_boundary() -> None:
    result = _ask_ped(semantic_fact="definition")

    assert len(result.response.sections) == 1
    assert result.response.sections[0].section_type == "DIRECT_ANSWER"
    assert "example:" not in result.released_text.casefold()
    assert "governed product knowledge" not in result.released_text.casefold()




def test_selected_definition_component_leads_with_plain_language_before_precise_detail() -> None:
    result = _ask_ped(semantic_fact="ped.definition")

    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "EDUCATION",
    ]
    assert result.response.sections[0].text == (
        "A Pre-Existing Disease (PED) is a health problem or medical condition "
        "you already had before your insurance started."
    )
    assert "not more than 36 months" in result.response.sections[1].text


def test_component_projection_keeps_boundary_metadata_internal() -> None:
    result = _ask_ped(semantic_fact="ped.waiting_period_relationship")

    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "EDUCATION",
    ]
    lowered = result.released_text.casefold()
    assert "health problem or medical condition you already had" in lowered
    assert "being treated as a ped does not by itself mean the condition is permanently excluded" in lowered
    assert "exact duration" in lowered
    assert "applicable product and policy terms" in lowered
    assert "this component does not state" not in lowered
    assert "does not promise that treatment will become payable" not in lowered

def test_applicability_projection_uses_concept_and_practical_implication_without_generic_boilerplate() -> None:
    result = _ask_ped(
        semantic_fact="applicability",
        requested_outcome="CONTEXTUAL_POLICY_EXPLANATION",
    )

    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "EDUCATION",
    ]
    lowered = result.released_text.casefold()
    assert "health problem or medical condition you already had" in lowered
    assert "policy may apply a ped waiting period" in lowered
    assert "customer-specific policy dates" not in lowered
    assert "governed product knowledge" not in lowered


def test_mechanics_projection_keeps_governed_example_and_product_boundary() -> None:
    result = _ask_ped(
        semantic_fact="mechanics",
        requested_outcome="INSURANCE_MECHANICS_EXPLANATION",
    )

    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "EXAMPLE",
        "CUSTOMER_QUALIFICATION",
    ]
    assert "example:" in result.released_text.casefold()
    assert "governed product knowledge" not in result.released_text.casefold()


def test_comparison_outcome_uses_comparison_shape_without_generic_example_dump() -> None:
    result = _ask_ped(
        semantic_fact="mechanics",
        requested_outcome="POLICY_FACT_COMPARISON",
    )

    assert [section.section_type for section in result.response.sections] == [
        "DIRECT_ANSWER",
        "CUSTOMER_QUALIFICATION",
    ]
    assert "example:" not in result.released_text.casefold()


def test_applicability_scenario_strips_interpreter_intent_summary_before_display() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            semantic_fact="applicability",
            requested_outcome="CONTEXTUAL_POLICY_EXPLANATION",
            scenario_facts=[
                {
                    "name": "context_detail",
                    "value": (
                        "diagnosed with a condition last year and considering buying health "
                        "insurance now; asks whether that condition would be covered"
                    ),
                }
            ],
        )
    )

    result = ask_health_question(
        question="Will the condition be covered if I buy health insurance now?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-scenario-summary-strip",
        execution_id="health-v0-scenario-summary-strip-execution",
        created_at="2026-11-22T13:00:00Z",
        education_repository=_ped_only_repository(),
    )

    first = result.response.sections[0].text
    assert first.startswith(
        "From what you shared — diagnosed with a condition last year and considering buying "
        "health insurance now — this is relevant to Pre-Existing Disease (PED)."
    )
    lowered = result.released_text.casefold()
    assert "asks whether" not in lowered
    assert "customer-specific policy dates" not in lowered
    assert "policy may apply a ped waiting period" in lowered


def test_contextual_answer_acknowledges_scenario_before_governed_detail() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            semantic_fact="ped.waiting_period_relationship",
            requested_outcome="CONTEXTUAL_POLICY_EXPLANATION",
            scenario_facts=[
                {"name": "context_detail", "value": "you were diagnosed with a condition before buying the policy"}
            ],
        )
    )

    result = ask_health_question(
        question="How would this affect a new policy?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-context-bridge",
        execution_id="health-v0-context-bridge-execution",
        created_at="2026-11-22T13:00:00Z",
        education_repository=_ped_only_repository(),
    )

    assert result.status == "ANSWER"
    assert result.response.sections[0].section_type == "DIRECT_ANSWER"
    first = result.response.sections[0].text
    assert first.startswith(
        "From what you shared — you were diagnosed with a condition before buying the policy — "
    )
    assert "this is relevant to Pre-Existing Disease (PED)." in first
    assert "health problem or medical condition you already had" in first
    assert "permanently excluded" in result.released_text
    assert "customer-specific policy dates" not in result.released_text.casefold()
    assert result.released_text.casefold().count("policy may apply a ped waiting period") == 1


def test_meta_scenario_fact_is_not_echoed_to_customer() -> None:
    provider = DeterministicFakeTextProvider(
        output_text=_resolved_output(
            "health:concept:pre_existing_disease",
            semantic_fact="ped.waiting_period_relationship",
            requested_outcome="CONTEXTUAL_POLICY_EXPLANATION",
            scenario_facts=[
                {"name": "context_detail", "value": "customer described a prior diagnosed condition"}
            ],
        )
    )

    result = ask_health_question(
        question="How would this affect a new policy?",
        provider=provider,
        model_name="test-model",
        request_id="health-v0-meta-scenario-fallback",
        execution_id="health-v0-meta-scenario-fallback-execution",
        created_at="2026-11-22T13:00:00Z",
        education_repository=_ped_only_repository(),
    )

    first = result.response.sections[0].text
    assert first.startswith("A Pre-Existing Disease (PED) is")
    assert "customer described" not in first.casefold()


def test_contextual_answer_falls_back_to_plain_language_without_scenario_fact() -> None:
    result = _ask_ped(
        semantic_fact="ped.waiting_period_relationship",
        requested_outcome="CONTEXTUAL_POLICY_EXPLANATION",
    )

    first = result.response.sections[0].text
    assert first.startswith("A Pre-Existing Disease (PED) is")
    assert "Based on the details you gave" not in first
    assert "This is relevant to" not in first


def test_ped_comparison_dimensions_component_provides_buying_checklist() -> None:
    result = _ask_ped(
        semantic_fact="ped.comparison_dimensions",
        requested_outcome="ADVISORY_DECISION_SUPPORT",
    )

    lowered = result.released_text.casefold()
    assert "compare the ped waiting-period rule" in lowered
    assert "exclusions or endorsements" in lowered
    assert "continuity or portability" in lowered
    assert "customer-specific policy dates" not in lowered
    assert lowered.count("policy may apply a ped waiting period") == 0
    assert "not a recommendation" not in lowered


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
