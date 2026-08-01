from dataclasses import replace

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.comparison import (
    BenefitComparisonError,
    ComparisonDimensionStatus,
    compare_normalized_benefits,
)
from insurance_intelligence.benefits.normalization import (
    BenefitComparisonProjection,
    CanonicalComparisonMechanic,
    normalize_for_comparison,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


@pytest.fixture
def star_projection():
    return normalize_for_comparison(STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION)


@pytest.fixture
def activ_projection():
    return normalize_for_comparison(ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)


@pytest.fixture
def result(star_projection, activ_projection):
    return compare_normalized_benefits(star_projection, activ_projection)


def _by_id(result):
    return {item.dimension_id: item for item in result.dimensions}


def test_comparison_preserves_concept_and_side_identities(result):
    assert result.concept_id == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.concept_id
    assert result.left.implementation_id == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.implementation_id
    assert result.right.implementation_id == ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id
    assert result.left.product_variant_id == STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.product_variant_id
    assert result.right.product_variant_id == ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.product_variant_id


def test_dimensions_are_deterministically_ordered(result):
    ids = tuple(item.dimension_id for item in result.dimensions)
    assert ids == tuple(sorted(ids))
    assert len(ids) == len(set(ids))


def test_normalized_restoration_amount_is_shared(result):
    item = _by_id(result)["restoration_amount_percentage_per_activation"]
    assert item.status is ComparisonDimensionStatus.SHARED
    assert item.left_value == item.right_value == 100
    assert item.unit == "percent_of_governed_base_sum_insured"


def test_restoration_frequency_type_is_a_factual_difference(result):
    item = _by_id(result)["restoration_frequency_type"]
    assert item.status is ComparisonDimensionStatus.DIFFERENT
    assert item.left_value == "FINITE"
    assert item.right_value == "UNLIMITED"


def test_restoration_frequency_count_is_a_factual_difference(result):
    item = _by_id(result)["restoration_frequency_count"]
    assert item.status is ComparisonDimensionStatus.DIFFERENT
    assert item.left_value == 1
    assert item.right_value is None
    assert item.unit == "activations_per_policy_period"


def test_same_hospitalization_use_is_a_factual_difference(result):
    item = _by_id(result)["same_hospitalization_use"]
    assert item.status is ComparisonDimensionStatus.DIFFERENT
    assert item.left_value is False
    assert item.right_value is True


def test_subsequent_hospitalization_use_is_shared(result):
    item = _by_id(result)["subsequent_hospitalization_use"]
    assert item.status is ComparisonDimensionStatus.SHARED
    assert item.left_value is True
    assert item.right_value is True


def test_activ_one_specific_first_claim_use_is_right_only(result):
    item = _by_id(result)["first_claim_use"]
    assert item.status is ComparisonDimensionStatus.RIGHT_ONLY
    assert item.left_value is None
    assert item.right_value is True
    assert item.left_evidence_reference_ids == ()
    assert item.right_evidence_reference_ids


def test_star_specific_same_illness_use_is_left_only(result):
    item = _by_id(result)["same_illness_use"]
    assert item.status is ComparisonDimensionStatus.LEFT_ONLY
    assert item.left_value is not None
    assert item.right_value is None
    assert item.left_evidence_reference_ids
    assert item.right_evidence_reference_ids == ()


def test_all_two_sided_dimensions_preserve_evidence_identities(result):
    for item in result.dimensions:
        if item.status not in {
            ComparisonDimensionStatus.LEFT_ONLY,
            ComparisonDimensionStatus.RIGHT_ONLY,
        }:
            assert item.left_evidence_reference_ids
            assert item.right_evidence_reference_ids


def test_source_dimension_identities_are_preserved_for_normalized_amount(result):
    item = _by_id(result)["restoration_amount_percentage_per_activation"]
    assert item.left_source_dimension_ids == ("restoration_percentage",)
    assert item.right_source_dimension_ids == ("restoration_percentage",)


def test_status_accessors_partition_the_result(result):
    partitions = (
        result.shared_dimensions,
        result.different_dimensions,
        result.blocked_dimensions,
        result.left_only_dimensions,
        result.right_only_dimensions,
    )
    assert sum(len(partition) for partition in partitions) == len(result.dimensions)
    assert result.shared_dimensions
    assert result.different_dimensions
    assert result.left_only_dimensions
    assert result.right_only_dimensions


def test_real_pair_has_no_blocked_normalized_dimensions(result):
    assert result.blocked_dimensions == ()


def test_comparison_includes_non_ranking_limitations(result):
    joined = " ".join(result.limitations).lower()
    assert "not a ranking" in joined
    assert "recommendation" in joined
    assert "entitlement" in joined
    assert "one-sided" in joined


def test_repeated_comparison_is_deterministic(star_projection, activ_projection):
    first = compare_normalized_benefits(star_projection, activ_projection)
    second = compare_normalized_benefits(star_projection, activ_projection)
    assert first == second


def test_reversing_sides_preserves_dimension_statuses_but_swaps_values(
    star_projection, activ_projection
):
    forward = compare_normalized_benefits(star_projection, activ_projection)
    reverse = compare_normalized_benefits(activ_projection, star_projection)
    forward_by_id = _by_id(forward)
    reverse_by_id = _by_id(reverse)
    assert set(forward_by_id) == set(reverse_by_id)
    assert forward_by_id["restoration_frequency_type"].left_value == reverse_by_id[
        "restoration_frequency_type"
    ].right_value
    assert forward_by_id["first_claim_use"].status is ComparisonDimensionStatus.RIGHT_ONLY
    assert reverse_by_id["first_claim_use"].status is ComparisonDimensionStatus.LEFT_ONLY


def test_comparison_blocks_a_shared_dimension_when_canonical_units_differ(
    star_projection, activ_projection
):
    activ_mechanics = dict(activ_projection.mechanics)
    source = activ_mechanics["restoration_amount_percentage_per_activation"]
    activ_mechanics[source.dimension_id] = replace(source, unit="different_canonical_unit")
    incompatible = BenefitComparisonProjection(
        implementation_id=activ_projection.implementation_id,
        concept_id=activ_projection.concept_id,
        insurer_id=activ_projection.insurer_id,
        product_id=activ_projection.product_id,
        product_variant_id=activ_projection.product_variant_id,
        mechanics=activ_mechanics,
    )
    result = compare_normalized_benefits(star_projection, incompatible)
    item = _by_id(result)["restoration_amount_percentage_per_activation"]
    assert item.status is ComparisonDimensionStatus.BLOCKED
    assert "canonical units differ" in item.reason
    assert item.unit is None


def test_rejects_self_comparison(star_projection):
    with pytest.raises(BenefitComparisonError, match="itself"):
        compare_normalized_benefits(star_projection, star_projection)


def test_rejects_concept_mismatch(star_projection, activ_projection):
    mismatched = BenefitComparisonProjection(
        implementation_id=activ_projection.implementation_id,
        concept_id="health:other:concept",
        insurer_id=activ_projection.insurer_id,
        product_id=activ_projection.product_id,
        product_variant_id=activ_projection.product_variant_id,
        mechanics=activ_projection.mechanics,
    )
    with pytest.raises(BenefitComparisonError, match="share one concept_id"):
        compare_normalized_benefits(star_projection, mismatched)


def test_rejects_non_projection_inputs(star_projection):
    with pytest.raises(BenefitComparisonError, match="left must"):
        compare_normalized_benefits(object(), star_projection)
    with pytest.raises(BenefitComparisonError, match="right must"):
        compare_normalized_benefits(star_projection, object())


def test_canonical_comparison_mechanic_requires_evidence():
    with pytest.raises(ValueError, match="evidence_reference_ids"):
        CanonicalComparisonMechanic(
            dimension_id="example",
            value=True,
            unit=None,
            source_dimension_ids=("source",),
            evidence_reference_ids=(),
        )
