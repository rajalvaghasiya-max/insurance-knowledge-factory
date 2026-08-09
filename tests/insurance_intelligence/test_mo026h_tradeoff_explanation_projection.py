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
    compare_product_assessment_profiles,
)
from insurance_intelligence.benefits.tradeoff_explanation_projection import (
    GovernedTradeoffExplanationProjection,
    TradeoffExplanationItem,
    TradeoffExplanationProjectionError,
    TradeoffExplanationProjectionStatus,
    project_tradeoff_explanation,
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
) -> BenefitAssessment:
    policy_id = None
    policy_version = None
    limitations = ()
    if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS}:
        policy_id = f"assessment_policy:health:{dimension_id}:v1"
        policy_version = "1.0"
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


def comparison(*, unresolved: bool = False):
    left_items = (
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
            status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
            band=AssessmentBand.RESTRICTIVE,
        ),
    )
    right_items = [
        assessment(
            assessment_id="right-restoration",
            dimension_id="restoration",
            role=DecisionRole.CORE_PROTECTION,
            status=AssessmentStatus.ASSESSED,
            band=AssessmentBand.VERY_STRONG,
        ),
        assessment(
            assessment_id="right-copay",
            dimension_id="copayment",
            role=DecisionRole.PROTECTION_FLOOR,
            status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
            band=AssessmentBand.RESTRICTIVE,
        ),
    ]
    if unresolved:
        right_items.append(
            assessment(
                assessment_id="right-room",
                dimension_id="room_rent_restriction",
                role=DecisionRole.PROTECTION_FLOOR,
                status=AssessmentStatus.NOT_SCORABLE,
                band=None,
            )
        )
    return compare_product_assessment_profiles(
        comparison_id="tradeoff:star-vs-activ-one:v1",
        left=profile(left=True, assessments=left_items),
        right=profile(left=False, assessments=tuple(right_items)),
    )


def test_projection_separates_local_strengths_shared_and_warnings() -> None:
    result = project_tradeoff_explanation(comparison())

    assert result.status is TradeoffExplanationProjectionStatus.READY
    assert [item.dimension_id for item in result.right_strengths] == ["restoration"]
    assert [item.dimension_id for item in result.shared_dimensions] == ["copayment"]
    assert [item.dimension_id for item in result.protection_floor_warnings] == ["copayment"]
    assert result.left_strengths == ()
    assert result.unresolved_dimensions == ()


def test_projection_preserves_source_limitations() -> None:
    result = project_tradeoff_explanation(comparison())
    warning = result.protection_floor_warnings[0]
    text = " ".join(warning.limitations)
    assert "left-copay source limitation" in text
    assert "right-copay source limitation" in text


def test_projection_marks_unresolved_dimensions_without_inference() -> None:
    result = project_tradeoff_explanation(comparison(unresolved=True))

    assert result.status is (
        TradeoffExplanationProjectionStatus.READY_WITH_UNRESOLVED_DIMENSIONS
    )
    assert [item.dimension_id for item in result.unresolved_dimensions] == [
        "room_rent_restriction"
    ]
    assert "must not be interpreted as superiority" in (
        result.unresolved_dimensions[0].statement.lower()
    )
    assert "room_rent_restriction" in [
        item.dimension_id for item in result.protection_floor_warnings
    ]


def test_projection_contains_mandatory_user_decides_boundary() -> None:
    result = project_tradeoff_explanation(comparison())
    boundary = result.decision_boundary.lower()
    assert "no overall winner" in boundary
    assert "user decides" in boundary
    assert "explicit request" in boundary
    assert "customer priorities/context" in boundary


def test_projection_has_no_ranking_or_recommendation_fields() -> None:
    result = project_tradeoff_explanation(comparison())
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


def test_projection_rejects_arbitrary_mapping() -> None:
    with pytest.raises(TradeoffExplanationProjectionError, match="exact"):
        project_tradeoff_explanation({"comparison_id": "x"})  # type: ignore[arg-type]


def test_projection_contract_requires_explicit_no_winner_boundary() -> None:
    with pytest.raises(TradeoffExplanationProjectionError, match="no overall winner"):
        GovernedTradeoffExplanationProjection(
            projection_id="projection:x",
            comparison_id="comparison:x",
            left_product_reference=LEFT_REF,
            right_product_reference=RIGHT_REF,
            status=TradeoffExplanationProjectionStatus.READY,
            left_strengths=(),
            right_strengths=(
                TradeoffExplanationItem(
                    dimension_id="restoration",
                    statement="Right is stronger on restoration.",
                    limitations=(),
                ),
            ),
            shared_dimensions=(),
            protection_floor_warnings=(),
            unresolved_dimensions=(),
            decision_boundary="Use the local trade-offs to decide.",
        )


def test_projection_is_deterministic() -> None:
    source = comparison(unresolved=True)
    assert project_tradeoff_explanation(source) == project_tradeoff_explanation(source)
