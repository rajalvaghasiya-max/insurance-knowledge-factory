from dataclasses import replace
from datetime import date

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.contracts import (
    MechanicValueType,
    PublicationStatus,
)
from insurance_intelligence.benefits.eligibility import (
    ComparisonEligibilityError,
    ComparisonEligibilityRequest,
    ComparisonEligibilityStatus,
    REQUIRED_COMPARISON_DIMENSIONS,
    evaluate_comparison_eligibility,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


AS_OF = date(2026, 7, 31)


def _request(left=STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION, right=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION):
    return ComparisonEligibilityRequest(left=left, right=right, as_of=AS_OF)


def test_real_restoration_pair_is_partially_eligible() -> None:
    result = evaluate_comparison_eligibility(_request())

    assert result.status is ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
    assert result.may_compare is True
    assert result.is_full_comparison is False
    assert result.concept_id == "health:coverage_capacity:restoration_benefit"


def test_real_pair_exposes_comparable_core_dimensions() -> None:
    result = evaluate_comparison_eligibility(_request())

    assert "trigger_requirement" in result.comparable_dimensions
    assert "same_hospitalization_use" in result.comparable_dimensions
    assert "subsequent_hospitalization_use" in result.comparable_dimensions


def test_real_pair_blocks_structurally_incompatible_dimensions() -> None:
    result = evaluate_comparison_eligibility(_request())

    assert result.blocked_dimensions == (
        "restoration_count_per_policy_period",
        "restoration_percentage",
    )
    assert any("incompatible value types or units" in reason for reason in result.reasons)


def test_real_pair_preserves_one_sided_dimensions() -> None:
    result = evaluate_comparison_eligibility(_request())

    assert "relapse_window_days" in result.left_only_dimensions
    assert "first_claim_use" in result.right_only_dimensions
    assert "partial_restoration_use" in result.right_only_dimensions


def test_required_dimension_contract_is_explicit() -> None:
    assert REQUIRED_COMPARISON_DIMENSIONS == (
        "restoration_percentage",
        "restoration_count_per_policy_period",
        "trigger_requirement",
        "same_hospitalization_use",
        "subsequent_hospitalization_use",
    )


def test_same_implementation_is_not_eligible() -> None:
    implementation = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION
    result = evaluate_comparison_eligibility(_request(implementation, implementation))

    assert result.status is ComparisonEligibilityStatus.NOT_ELIGIBLE
    assert result.may_compare is False
    assert any("distinct implementation" in reason for reason in result.reasons)


def test_concept_mismatch_is_not_eligible() -> None:
    right = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        concept_id="health:unrelated:benefit",
    )
    result = evaluate_comparison_eligibility(_request(right=right))

    assert result.status is ComparisonEligibilityStatus.NOT_ELIGIBLE
    assert result.concept_id is None
    assert any("same canonical benefit concept" in reason for reason in result.reasons)


def test_unpublished_implementation_is_not_eligible() -> None:
    right = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        publication_status=PublicationStatus.NOT_PUBLISHED,
    )
    result = evaluate_comparison_eligibility(_request(right=right))

    assert result.status is ComparisonEligibilityStatus.NOT_ELIGIBLE
    assert any("right implementation is not approved and published" in reason for reason in result.reasons)


def test_inactive_implementation_is_not_eligible() -> None:
    right = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        effective_from=date(2027, 1, 1),
    )
    result = evaluate_comparison_eligibility(_request(right=right))

    assert result.status is ComparisonEligibilityStatus.NOT_ELIGIBLE
    assert any("right implementation is not active" in reason for reason in result.reasons)


def test_insufficient_required_overlap_is_not_eligible() -> None:
    right = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        mechanics=(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics[0],),
    )
    result = evaluate_comparison_eligibility(_request(right=right))

    assert result.status is ComparisonEligibilityStatus.NOT_ELIGIBLE
    assert len(result.missing_required_right) == 4
    assert any("insufficient required mechanic overlap" in reason for reason in result.reasons)


def test_missing_required_dimensions_are_reported_per_side() -> None:
    left = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        mechanics=tuple(
            mechanic
            for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
            if mechanic.dimension_id != "same_hospitalization_use"
        ),
    )
    result = evaluate_comparison_eligibility(_request(left=left))

    assert result.missing_required_left == ("same_hospitalization_use",)
    assert result.missing_required_right == ()


def test_normalized_required_mechanics_can_be_fully_eligible() -> None:
    left_by_dimension = {
        mechanic.dimension_id: mechanic
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    }
    normalized_right_mechanics = tuple(
        replace(
            mechanic,
            value_type=left_by_dimension[mechanic.dimension_id].value_type,
            unit=left_by_dimension[mechanic.dimension_id].unit,
            value=(
                2
                if mechanic.dimension_id == "restoration_count_per_policy_period"
                else mechanic.value
            ),
        )
        if mechanic.dimension_id in REQUIRED_COMPARISON_DIMENSIONS
        else mechanic
        for mechanic in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
    )
    right = replace(
        ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
        mechanics=normalized_right_mechanics,
    )

    result = evaluate_comparison_eligibility(_request(right=right))

    assert result.status is ComparisonEligibilityStatus.ELIGIBLE
    assert result.is_full_comparison is True
    assert set(REQUIRED_COMPARISON_DIMENSIONS) <= set(result.comparable_dimensions)


def test_gate_does_not_compare_values_or_choose_a_product() -> None:
    result = evaluate_comparison_eligibility(_request())

    assert not hasattr(result, "winner")
    assert not hasattr(result, "ranking")
    assert not hasattr(result, "recommendation")
    assert not hasattr(result, "entitlement")


def test_request_rejects_invalid_left() -> None:
    with pytest.raises(ComparisonEligibilityError, match="left"):
        ComparisonEligibilityRequest(  # type: ignore[arg-type]
            left="invalid",
            right=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
            as_of=AS_OF,
        )


def test_request_rejects_invalid_date() -> None:
    with pytest.raises(ComparisonEligibilityError, match="as_of"):
        ComparisonEligibilityRequest(  # type: ignore[arg-type]
            left=STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
            right=ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
            as_of="2026-07-31",
        )


def test_gate_rejects_invalid_request_type() -> None:
    with pytest.raises(ComparisonEligibilityError, match="request"):
        evaluate_comparison_eligibility("invalid")  # type: ignore[arg-type]


def test_count_and_status_properties_are_deterministic() -> None:
    first = evaluate_comparison_eligibility(_request())
    second = evaluate_comparison_eligibility(_request())

    assert first == second
    assert first.left_implementation_id.startswith("benefit_impl:star_health")
    assert first.right_implementation_id.startswith("benefit_impl:aditya_birla_health")
