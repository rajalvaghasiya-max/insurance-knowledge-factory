from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_PRODUCT_VARIANT_ID,
    ACTIV_ONE_NXT_RESTORATION_EVIDENCE,
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_BENEFIT_CONCEPT
from insurance_intelligence.benefits.contracts import (
    BenefitAvailability,
    BenefitImplementationType,
    MechanicValueType,
)


def _mechanic(dimension_id: str):
    return next(
        item
        for item in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
        if item.dimension_id == dimension_id
    )


def test_activ_one_nxt_identity_is_variant_specific() -> None:
    implementation = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert implementation.insurer_id == "aditya_birla_health"
    assert implementation.product_id == "activ_one"
    assert implementation.product_variant_id == ACTIV_ONE_NXT_PRODUCT_VARIANT_ID
    assert implementation.marketing_name == "Super Reload"
    assert "nxt" in implementation.product_variant_id


def test_activ_one_nxt_super_reload_is_governed_built_in_cover() -> None:
    implementation = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION

    assert implementation.availability is BenefitAvailability.INCLUDED
    assert implementation.implementation_type is BenefitImplementationType.BUILT_IN
    assert implementation.is_governed_for_use is True
    assert implementation.is_active(date(2026, 7, 31)) is True


def test_activ_one_nxt_uses_exact_document_hashes() -> None:
    hashes = {item.authority_type: item.source_sha256 for item in ACTIV_ONE_NXT_RESTORATION_EVIDENCE}

    assert hashes == {
        "policy_wording": "d7726811cfdf2c3c31c3750eb0bd4a55203b20cf79d44fc6849dbc77ba556451",
        "prospectus": "8923d6457d368c9d80d097032a7b784c65b30ba07ae68ea7474af7569332fa56",
    }


def test_activ_one_nxt_reload_is_up_to_full_base_sum_insured() -> None:
    restoration = _mechanic("restoration_percentage")
    per_claim = _mechanic("maximum_liability_per_claim_percentage")

    assert restoration.value_type is MechanicValueType.PERCENTAGE
    assert restoration.value == 100
    assert restoration.unit == "percent_of_base_sum_insured_per_activation"
    assert per_claim.value == 100
    assert per_claim.unit == "percent_of_base_sum_insured"


def test_activ_one_nxt_reload_is_unlimited_per_policy_year() -> None:
    count = _mechanic("restoration_count_per_policy_period")
    reset = _mechanic("policy_year_reset")

    assert count.value == "unlimited_during_policy_year"
    assert reset.value is True


def test_activ_one_nxt_trigger_includes_exhaustion_or_insufficiency() -> None:
    trigger = _mechanic("trigger_requirement")

    assert trigger.value == (
        "base_sum_insured_and_accumulated_super_credit_exhausted_or_insufficient_for_claim"
    )


def test_activ_one_nxt_supports_same_claim_and_first_claim_use() -> None:
    assert _mechanic("same_hospitalization_use").value is True
    assert _mechanic("first_claim_use").value is True
    assert _mechanic("subsequent_hospitalization_use").value is True


def test_activ_one_nxt_supports_partial_reload() -> None:
    partial = _mechanic("partial_restoration_use")

    assert partial.value is True
    assert partial.evidence_reference_ids == (
        "ev_activ_one_nxt_super_reload_prospectus",
    )


def test_activ_one_nxt_preserves_scope_and_utilization_sequence() -> None:
    scope = _mechanic("covered_section_scope")
    sequence = _mechanic("utilization_sequence")

    assert "C.1 Hospitalization Treatment" in scope.value
    assert "C.7 Organ Donor Expenses" in scope.value
    assert sequence.value == (
        "Base Sum Insured -> Super Credit (if applicable) -> Super Reload -> "
        "Cancer Booster (if applicable)"
    )


def test_activ_one_nxt_record_validates_against_canonical_concept() -> None:
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.validate_against(
        RESTORATION_BENEFIT_CONCEPT
    )


def test_unsupported_mechanics_are_explicitly_not_asserted() -> None:
    implementation = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION
    dimensions = {item.dimension_id for item in implementation.mechanics}

    assert "same_illness_use" not in dimensions
    assert "carry_over_between_policy_years" not in dimensions
    assert any("related-versus-unrelated illness" in item for item in implementation.exclusions)
    assert any("carry-forward" in item for item in implementation.exclusions)
