from __future__ import annotations

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import (
    RESTORATION_BENEFIT_CONCEPT,
    RESTORATION_CONCEPT_ID,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.terminology.health_seed import build_health_concept_registry_v1


def _mechanics(implementation) -> dict[str, object]:
    return {item.dimension_id: item.value for item in implementation.mechanics}


def test_recharge_is_a_routing_alias_not_a_separate_governed_benefit_concept() -> None:
    terminology = build_health_concept_registry_v1().get("health:concept:restoration")

    assert terminology.downstream_topic == "restoration"
    assert "restoration benefit" in terminology.aliases
    assert "recharge benefit" in terminology.aliases
    assert RESTORATION_BENEFIT_CONCEPT.concept_id == RESTORATION_CONCEPT_ID
    assert RESTORATION_BENEFIT_CONCEPT.canonical_name == "Restoration of Sum Insured"


def test_restoration_concept_requires_product_specific_trigger_and_use_mechanics() -> None:
    dimensions = set(RESTORATION_BENEFIT_CONCEPT.allowed_mechanic_dimensions)

    assert {
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "trigger_timing",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
        "same_illness_use",
    } <= dimensions
    assert "recharge" not in RESTORATION_BENEFIT_CONCEPT.definition.casefold()


def test_star_restoration_preserves_its_product_specific_trigger_semantics() -> None:
    mechanics = _mechanics(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)

    assert STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.concept_id == RESTORATION_CONCEPT_ID
    assert STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.marketing_name == (
        "Automatic Restoration of Sum Insured"
    )
    assert mechanics["restoration_percentage"] == 100
    assert mechanics["restoration_count_per_policy_period"] == 1
    assert mechanics["trigger_requirement"] == (
        "exhaustion_of_basic_sum_insured_and_accrued_cumulative_bonus_if_any"
    )
    assert mechanics["trigger_timing"] == "immediately_upon_exhaustion"
    assert mechanics["same_hospitalization_use"] is False
    assert mechanics["subsequent_hospitalization_use"] is True
    assert mechanics["same_illness_use"] is True


def test_super_reload_shares_concept_but_not_star_mechanics() -> None:
    star = _mechanics(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    activ = _mechanics(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.concept_id == RESTORATION_CONCEPT_ID
    assert ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.marketing_name == "Super Reload"
    assert activ["restoration_percentage"] == 100
    assert activ["restoration_count_per_policy_period"] == "unlimited_during_policy_year"
    assert activ["trigger_requirement"] == (
        "base_sum_insured_and_accumulated_super_credit_exhausted_or_insufficient_for_claim"
    )
    assert activ["trigger_timing"] == (
        "within_admissible_claim_when_available_capacity_is_insufficient"
    )
    assert activ["same_hospitalization_use"] is True
    assert activ["subsequent_hospitalization_use"] is True

    assert star["restoration_count_per_policy_period"] != activ[
        "restoration_count_per_policy_period"
    ]
    assert star["trigger_requirement"] != activ["trigger_requirement"]
    assert star["trigger_timing"] != activ["trigger_timing"]
    assert star["same_hospitalization_use"] != activ["same_hospitalization_use"]


def test_marketing_language_cannot_determine_restoration_mechanics() -> None:
    star = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION
    activ = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert star.marketing_name != activ.marketing_name
    assert star.concept_id == activ.concept_id
    assert star.behaviour_signature_id != activ.behaviour_signature_id
    assert "once_after_full_exhaustion_subsequent_hospitalization" in star.behaviour_signature_id
    assert "unlimited_exhausted_or_insufficient_same_claim" in activ.behaviour_signature_id


def test_same_concept_does_not_imply_same_customer_entitlement_or_claim_behavior() -> None:
    star = _mechanics(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    activ = _mechanics(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert star["same_hospitalization_use"] is False
    assert activ["same_hospitalization_use"] is True
    assert "No entitlement or claim-payment conclusion" in " ".join(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.exclusions
    )
    assert all(
        term not in RESTORATION_BENEFIT_CONCEPT.definition.casefold()
        for term in ("star", "activ one", "super reload")
    )
