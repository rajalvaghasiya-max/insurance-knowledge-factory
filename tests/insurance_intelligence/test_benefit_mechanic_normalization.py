from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.contracts import (
    BenefitMechanic,
    MechanicValueType,
    PublicationStatus,
)
from insurance_intelligence.benefits.normalization import (
    BenefitComparisonProjection,
    MechanicNormalizationError,
    RestorationFrequencyType,
    normalize_for_comparison,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


def test_star_projection_preserves_identity() -> None:
    projection = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)

    assert isinstance(projection, BenefitComparisonProjection)
    assert projection.implementation_id == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.implementation_id
    assert projection.insurer_id == "star_health"
    assert projection.product_id == "star_comprehensive"
    assert projection.product_variant_id == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.product_variant_id


def test_activ_one_projection_preserves_identity() -> None:
    projection = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert projection.implementation_id == ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id
    assert projection.insurer_id == "aditya_birla_health"
    assert projection.product_id == "activ_one"
    assert projection.product_variant_id == ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.product_variant_id


def test_restoration_amount_is_normalized_to_common_dimension_and_unit() -> None:
    star = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    activ = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    star_amount = star.mechanics["restoration_amount_percentage_per_activation"]
    activ_amount = activ.mechanics["restoration_amount_percentage_per_activation"]

    assert star_amount.value == activ_amount.value == 100
    assert star_amount.unit == activ_amount.unit == "percent_of_governed_base_sum_insured"
    assert star_amount.source_dimension_ids == ("restoration_percentage",)
    assert activ_amount.source_dimension_ids == ("restoration_percentage",)


def test_star_frequency_is_projected_as_finite_count_one() -> None:
    projection = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)

    assert projection.mechanics["restoration_frequency_type"].value == RestorationFrequencyType.FINITE.value
    assert projection.mechanics["restoration_frequency_count"].value == 1
    assert projection.mechanics["restoration_frequency_count"].unit == "activations_per_policy_period"


def test_activ_one_frequency_is_projected_as_unlimited_without_count() -> None:
    projection = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert projection.mechanics["restoration_frequency_type"].value == RestorationFrequencyType.UNLIMITED.value
    assert projection.mechanics["restoration_frequency_count"].value is None
    assert projection.mechanics["restoration_frequency_count"].unit == "activations_per_policy_period"


def test_normalization_does_not_mutate_source_catalogue_records() -> None:
    star_before = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    activ_before = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics

    normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics is star_before
    assert ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics is activ_before
    assert next(item for item in star_before if item.dimension_id == "restoration_percentage").unit == "percent_of_basic_sum_insured"
    assert next(item for item in activ_before if item.dimension_id == "restoration_percentage").unit == "percent_of_base_sum_insured_per_activation"


def test_evidence_references_are_preserved_on_normalized_amount() -> None:
    projection = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    source = next(
        mechanic
        for mechanic in ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.mechanics
        if mechanic.dimension_id == "restoration_percentage"
    )

    assert projection.mechanics["restoration_amount_percentage_per_activation"].evidence_reference_ids == source.evidence_reference_ids


def test_passthrough_mechanics_preserve_values() -> None:
    projection = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)

    assert projection.mechanics["trigger_requirement"].value == "exhaustion_of_basic_sum_insured_and_accrued_cumulative_bonus_if_any"
    assert projection.mechanics["same_hospitalization_use"].value is False
    assert projection.mechanics["subsequent_hospitalization_use"].value is True
    assert projection.mechanics["policy_year_reset"].value is True


def test_variant_specific_dimensions_remain_one_sided() -> None:
    star = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)
    activ = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert "first_claim_use" not in star.mechanics
    assert activ.mechanics["first_claim_use"].value is True
    assert "partial_restoration_use" not in star.mechanics
    assert activ.mechanics["partial_restoration_use"].value is True
    assert "relapse_window_days" in star.mechanics
    assert "relapse_window_days" not in activ.mechanics


def test_dimension_ids_are_deterministically_sorted() -> None:
    projection = normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)

    assert projection.dimension_ids == tuple(sorted(projection.mechanics))


def test_projection_mechanics_are_immutable() -> None:
    projection = normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)

    with pytest.raises(TypeError):
        projection.mechanics["new_dimension"] = projection.mechanics["trigger_requirement"]  # type: ignore[index]


def test_rejects_non_implementation_input() -> None:
    with pytest.raises(MechanicNormalizationError, match="ProductBenefitImplementation"):
        normalize_for_comparison(object())  # type: ignore[arg-type]


def test_rejects_unpublished_implementation() -> None:
    unpublished = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        publication_status=PublicationStatus.NOT_PUBLISHED,
    )

    with pytest.raises(MechanicNormalizationError, match="approved and published"):
        normalize_for_comparison(unpublished)


def test_rejects_missing_restoration_percentage() -> None:
    implementation = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        mechanics=tuple(
            mechanic
            for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
            if mechanic.dimension_id != "restoration_percentage"
        ),
    )

    with pytest.raises(MechanicNormalizationError, match="restoration_percentage is required"):
        normalize_for_comparison(implementation)


def test_rejects_unsupported_restoration_percentage_unit() -> None:
    mechanics = tuple(
        replace(mechanic, unit="percent_of_unknown_basis")
        if mechanic.dimension_id == "restoration_percentage"
        else mechanic
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    )
    implementation = replace(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION, mechanics=mechanics)

    with pytest.raises(MechanicNormalizationError, match="unsupported restoration percentage unit"):
        normalize_for_comparison(implementation)


def test_rejects_unsupported_restoration_percentage_value() -> None:
    mechanics = tuple(
        replace(mechanic, value=50)
        if mechanic.dimension_id == "restoration_percentage"
        else mechanic
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    )
    implementation = replace(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION, mechanics=mechanics)

    with pytest.raises(MechanicNormalizationError, match="100 percent"):
        normalize_for_comparison(implementation)


def test_rejects_unsupported_frequency_representation() -> None:
    mechanics = tuple(
        BenefitMechanic(
            dimension_id=mechanic.dimension_id,
            value_type=MechanicValueType.ENUM,
            value="twice_when_needed",
            unit=mechanic.unit,
            applicability=mechanic.applicability,
            evidence_reference_ids=mechanic.evidence_reference_ids,
        )
        if mechanic.dimension_id == "restoration_count_per_policy_period"
        else mechanic
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    )
    implementation = replace(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION, mechanics=mechanics)

    with pytest.raises(MechanicNormalizationError, match="unsupported restoration frequency"):
        normalize_for_comparison(implementation)


def test_rejects_non_positive_finite_frequency() -> None:
    mechanics = tuple(
        replace(mechanic, value=0)
        if mechanic.dimension_id == "restoration_count_per_policy_period"
        else mechanic
        for mechanic in STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.mechanics
    )
    implementation = replace(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION, mechanics=mechanics)

    with pytest.raises(MechanicNormalizationError, match="must be positive"):
        normalize_for_comparison(implementation)
