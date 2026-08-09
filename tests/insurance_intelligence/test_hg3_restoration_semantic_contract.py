from __future__ import annotations

from insurance_intelligence.benefits.catalogue import (
    RESTORATION_BENEFIT_CONCEPT,
    RESTORATION_CONCEPT_ID,
)
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


REQUIRED_RESTORATION_MECHANICS = {
    "restoration_percentage",
    "restoration_count_per_policy_period",
    "trigger_requirement",
    "trigger_timing",
    "same_hospitalization_use",
    "subsequent_hospitalization_use",
    "first_claim_use",
    "partial_restoration_use",
    "maximum_liability_per_claim_percentage",
    "covered_section_scope",
    "utilization_sequence",
    "policy_year_reset",
    "floater_operation",
}

FORBIDDEN_DECISION_SEMANTICS = {
    "comparison",
    "ranking",
    "recommendation",
    "suitability",
    "entitlement",
    "claim_payment",
    "claim_outcome",
}


def test_health_terminology_routes_restoration_to_restoration_topic() -> None:
    registry = build_health_concept_registry_v1()
    restoration = registry.get("health:concept:restoration")

    assert restoration.concept.canonical_name == "Restoration of sum insured"
    assert restoration.concept_type == "BENEFIT"
    assert restoration.downstream_topic == "restoration"
    assert "restoration benefit" in restoration.aliases
    assert "recharge benefit" in restoration.aliases


def test_restoration_benefit_concept_is_product_neutral_and_governed() -> None:
    concept = RESTORATION_BENEFIT_CONCEPT

    assert concept.concept_id == RESTORATION_CONCEPT_ID
    assert concept.concept_id == "health:coverage_capacity:restoration_benefit"
    assert concept.canonical_name == "Restoration of Sum Insured"
    assert concept.benefit_family == "sum_insured_behavior"
    assert concept.review_status is ReviewStatus.APPROVED
    assert concept.publication_status is PublicationStatus.PUBLISHED
    assert concept.is_governed_for_use is True

    lowered = " ".join(
        (
            concept.concept_id,
            concept.canonical_name,
            concept.definition,
            concept.benefit_family,
            *concept.allowed_mechanic_dimensions,
        )
    ).casefold()

    assert "star" not in lowered
    assert "aditya" not in lowered
    assert "activ one" not in lowered
    assert "super reload" not in lowered


def test_restoration_contract_supports_activ_one_pilot_semantics_without_product_hacks() -> None:
    dimensions = set(RESTORATION_BENEFIT_CONCEPT.allowed_mechanic_dimensions)

    assert REQUIRED_RESTORATION_MECHANICS <= dimensions


def test_restoration_contract_keeps_optional_cross_product_mechanics_explicit() -> None:
    dimensions = set(RESTORATION_BENEFIT_CONCEPT.allowed_mechanic_dimensions)

    assert {
        "same_illness_use",
        "relapse_window_days",
        "carry_over_between_policy_years",
    } <= dimensions


def test_restoration_concept_does_not_encode_decision_or_claim_outcome_semantics() -> None:
    dimensions = set(RESTORATION_BENEFIT_CONCEPT.allowed_mechanic_dimensions)

    assert dimensions.isdisjoint(FORBIDDEN_DECISION_SEMANTICS)

    text = " ".join(
        (
            RESTORATION_BENEFIT_CONCEPT.definition,
            RESTORATION_BENEFIT_CONCEPT.benefit_family,
            *RESTORATION_BENEFIT_CONCEPT.allowed_mechanic_dimensions,
        )
    ).casefold()

    for forbidden in FORBIDDEN_DECISION_SEMANTICS:
        assert forbidden not in text


def test_terminology_and_benefit_concepts_remain_separate_layers() -> None:
    registry = build_health_concept_registry_v1()
    terminology = registry.get("health:concept:restoration")

    assert terminology.concept.concept_family_id != RESTORATION_BENEFIT_CONCEPT.concept_id
    assert terminology.downstream_topic == "restoration"
    assert RESTORATION_BENEFIT_CONCEPT.benefit_family == "sum_insured_behavior"
