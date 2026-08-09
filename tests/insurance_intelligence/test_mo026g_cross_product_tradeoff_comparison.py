from dataclasses import replace

import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.product_assessment_profile import (
    ProductAssessmentEntry,
    build_product_assessment_profile,
)
from insurance_intelligence.benefits.tradeoff_comparison import (
    DimensionTradeoffStatus,
    TradeoffComparisonError,
    compare_product_assessment_profiles,
)


LEFT_REF = "star_health:star_comprehensive:pv_star:SHAHLIP26044V092526"
RIGHT_REF = (
    "aditya_birla_health:activ_one:"
    "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324:"
    "ADIHLIP24097V012324"
)


def assessment(
    *,
    assessment_id: str,
    dimension_id: str,
    role: DecisionRole,
    status: AssessmentStatus,
    band: AssessmentBand | None,
    policy_id: str | None = None,
    policy_version: str | None = None,
) -> BenefitAssessment:
    if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS}:
        policy_id = policy_id or f"assessment_policy:health:{dimension_id}:v1"
        policy_version = policy_version or "1.0"
    limitations = ()
    if status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS:
        limitations = (f"{assessment_id} source limitation.",)
    elif status is AssessmentStatus.NOT_SCORABLE:
        limitations = (f"{assessment_id} unresolved governed mechanic.",)

    return BenefitAssessment(
        assessment_id=assessment_id,
        implementation_id=f"impl:{assessment_id}",
        concept_id=f"health:test:{dimension_id}",
        dimension_id=dimension_id,
        decision_role=role,
        status=status,
        assessment_band=band,
        assessment_policy_id=policy_id,
        assessment_policy_version=policy_version,
        summary=f"Summary for {assessment_id}",
        practical_meaning=f"Meaning for {assessment_id}",
        source_mechanic_ids=(f"{dimension_id}_mechanic",),
        evidence_reference_ids=(f"evidence:{assessment_id}",),
        limitations=limitations,
    )


def profile(*, left: bool, assessments: tuple[BenefitAssessment, ...]):
    if left:
        insurer_id = "star_health"
        product_id = "star_comprehensive"
        variant_id = "pv_star"
        uin = "SHAHLIP26044V092526"
        reference = LEFT_REF
        profile_id = "profile:star:v1"
    else:
        insurer_id = "aditya_birla_health"
        product_id = "activ_one"
        variant_id = "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
        uin = "ADIHLIP24097V012324"
        reference = RIGHT_REF
        profile_id = "profile:activ_one_nxt:v1"

    return build_product_assessment_profile(
        profile_id=profile_id,
        insurer_id=insurer_id,
        product_id=product_id,
        product_variant_id=variant_id,
        product_uin=uin,
        entries=tuple(
            ProductAssessmentEntry(product_reference=reference, assessment=item)
            for item in assessments
        ),
    )


def compare(left_assessments, right_assessments):
    return compare_product_assessment_profiles(
        comparison_id="tradeoff:star-vs-activ-one:v1",
        left=profile(left=True, assessments=tuple(left_assessments)),
        right=profile(left=False, assessments=tuple(right_assessments)),
    )


def test_common_dimension_reports_left_stronger_without_overall_winner() -> None:
    left = assessment(
        assessment_id="left-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.VERY_STRONG,
    )
    right = assessment(
        assessment_id="right-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    result = compare((left,), (right,))

    item = result.dimensions[0]
    assert item.status is DimensionTradeoffStatus.LEFT_STRONGER
    assert "left product is stronger on this dimension" in item.explanation.lower()
    assert result.left_stronger_dimensions == (item,)
    forbidden = {
        "overall_score",
        "score",
        "rank",
        "winner",
        "weight",
        "recommendation",
        "suitability",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)


def test_common_dimension_reports_right_stronger() -> None:
    left = assessment(
        assessment_id="left-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_RESTRICTIVE,
    )
    right = assessment(
        assessment_id="right-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.RESTRICTIVE,
    )
    result = compare((left,), (right,))
    item = result.dimensions[0]

    assert item.status is DimensionTradeoffStatus.RIGHT_STRONGER
    assert result.right_stronger_dimensions == (item,)
    assert item in result.protection_floor_warnings
    assert "left-copay source limitation" in " ".join(item.limitations)
    assert "right-copay source limitation" in " ".join(item.limitations)


def test_equal_bands_are_shared_not_a_tie_winner() -> None:
    left = assessment(
        assessment_id="left-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    right = assessment(
        assessment_id="right-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    item = compare((left,), (right,)).dimensions[0]
    assert item.status is DimensionTradeoffStatus.SHARED
    assert "same governed qualitative band" in item.explanation.lower()


def test_unresolved_side_blocks_stronger_weaker_conclusion() -> None:
    left = assessment(
        assessment_id="left-room",
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.NOT_SCORABLE,
        band=None,
    )
    right = assessment(
        assessment_id="right-room",
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.VERY_STRONG,
    )
    result = compare((left,), (right,))
    item = result.dimensions[0]

    assert item.status is DimensionTradeoffStatus.UNRESOLVED
    assert item in result.unresolved_dimensions
    assert item in result.protection_floor_warnings
    assert "no stronger/weaker conclusion" in " ".join(item.limitations).lower()


def test_different_policy_versions_are_not_compared() -> None:
    left = assessment(
        assessment_id="left-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.VERY_STRONG,
        policy_version="1.0",
    )
    right = assessment(
        assessment_id="right-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
        policy_version="2.0",
    )
    item = compare((left,), (right,)).dimensions[0]

    assert item.status is DimensionTradeoffStatus.NOT_COMPARABLE
    assert "common governed assessment policy" in " ".join(item.limitations).lower()


def test_one_sided_dimension_does_not_imply_superiority() -> None:
    left = assessment(
        assessment_id="left-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.RESTRICTIVE,
    )
    right = assessment(
        assessment_id="right-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.VERY_STRONG,
    )
    result = compare((left,), (right,))

    by_id = {item.dimension_id: item for item in result.dimensions}
    assert by_id["copayment"].status is DimensionTradeoffStatus.LEFT_ONLY
    assert by_id["restoration"].status is DimensionTradeoffStatus.RIGHT_ONLY
    assert "must not be interpreted as superiority" in by_id["copayment"].explanation.lower()
    assert "must not be interpreted as superiority" in by_id["restoration"].explanation.lower()


def test_comparison_orders_union_of_dimensions_deterministically() -> None:
    left = (
        assessment(
            assessment_id="left-restoration",
            dimension_id="restoration",
            role=DecisionRole.CORE_PROTECTION,
            status=AssessmentStatus.ASSESSED,
            band=AssessmentBand.STRONG,
        ),
        assessment(
            assessment_id="left-copay",
            dimension_id="copayment",
            role=DecisionRole.PROTECTION_FLOOR,
            status=AssessmentStatus.ASSESSED,
            band=AssessmentBand.RESTRICTIVE,
        ),
    )
    right = (
        assessment(
            assessment_id="right-room",
            dimension_id="room_rent_restriction",
            role=DecisionRole.PROTECTION_FLOOR,
            status=AssessmentStatus.NOT_SCORABLE,
            band=None,
        ),
        assessment(
            assessment_id="right-restoration",
            dimension_id="restoration",
            role=DecisionRole.CORE_PROTECTION,
            status=AssessmentStatus.ASSESSED,
            band=AssessmentBand.VERY_STRONG,
        ),
    )
    result = compare(left, right)
    assert [item.dimension_id for item in result.dimensions] == [
        "copayment",
        "restoration",
        "room_rent_restriction",
    ]


def test_decision_role_mismatch_fails_closed() -> None:
    left = assessment(
        assessment_id="left-x",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    right = assessment(
        assessment_id="right-x",
        dimension_id="restoration",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    with pytest.raises(TradeoffComparisonError, match="decision-role mismatch"):
        compare((left,), (right,))


def test_comparison_rejects_same_product_profile() -> None:
    item = assessment(
        assessment_id="left-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    left = profile(left=True, assessments=(item,))
    with pytest.raises(TradeoffComparisonError, match="itself"):
        compare_product_assessment_profiles(
            comparison_id="invalid",
            left=left,
            right=left,
        )


def test_comparison_preserves_source_assessments_unchanged() -> None:
    left = assessment(
        assessment_id="left-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.STRONG,
    )
    right = assessment(
        assessment_id="right-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_STRONG,
    )
    left_original = replace(left)
    right_original = replace(right)
    item = compare((left,), (right,)).dimensions[0]

    assert item.left_assessment == left_original
    assert item.right_assessment == right_original
    assert left == left_original
    assert right == right_original
