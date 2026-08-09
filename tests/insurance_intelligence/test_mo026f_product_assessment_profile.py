import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    BenefitInteractionReference,
    DecisionRole,
    InteractionSeverity,
    InteractionType,
)
from insurance_intelligence.benefits.product_assessment_profile import (
    ProductAssessmentEntry,
    ProductAssessmentProfileError,
    ProfileDimensionDisposition,
    build_product_assessment_profile,
)


PRODUCT_REFERENCE = (
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
    interactions: tuple[BenefitInteractionReference, ...] = (),
) -> BenefitAssessment:
    limitations = ()
    policy_id = None
    policy_version = None
    if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS}:
        policy_id = f"assessment_policy:health:{dimension_id}:v1"
        policy_version = "1.0"
    if status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS:
        limitations = ("Governed source limitation remains visible.",)
    elif status is AssessmentStatus.NOT_SCORABLE:
        limitations = ("Required governed mechanic remains unresolved.",)

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
        summary=f"Summary for {dimension_id}",
        practical_meaning=f"Meaning for {dimension_id}",
        source_mechanic_ids=(f"{dimension_id}_mechanic",),
        evidence_reference_ids=(f"evidence:{dimension_id}",),
        limitations=limitations,
        interaction_references=interactions,
    )


def entry(item: BenefitAssessment, *, product_reference: str = PRODUCT_REFERENCE):
    return ProductAssessmentEntry(
        product_reference=product_reference,
        assessment=item,
    )


def profile(*entries: ProductAssessmentEntry):
    return build_product_assessment_profile(
        profile_id="assessment_profile:activ_one_nxt:v1",
        insurer_id="aditya_birla_health",
        product_id="activ_one",
        product_variant_id="pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324",
        product_uin="ADIHLIP24097V012324",
        entries=tuple(entries),
    )


def test_profile_groups_strength_restriction_and_unknown_without_overall_score() -> None:
    restoration = assessment(
        assessment_id="a-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_STRONG,
    )
    copay = assessment(
        assessment_id="a-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.RESTRICTIVE,
    )
    room_rent = assessment(
        assessment_id="a-room-rent",
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.NOT_SCORABLE,
        band=None,
    )

    result = profile(entry(restoration), entry(copay), entry(room_rent))

    assert [item.assessment.dimension_id for item in result.strengths] == ["restoration"]
    assert [item.assessment.dimension_id for item in result.restrictions] == ["copayment"]
    assert [item.assessment.dimension_id for item in result.unknowns] == [
        "room_rent_restriction"
    ]
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


def test_profile_keeps_protection_floor_restrictions_and_unknowns_visible() -> None:
    copay = assessment(
        assessment_id="a-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.RESTRICTIVE,
    )
    room_rent = assessment(
        assessment_id="a-room-rent",
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.NOT_SCORABLE,
        band=None,
    )
    result = profile(entry(copay), entry(room_rent))

    assert [item.assessment.dimension_id for item in result.protection_floor_warnings] == [
        "copayment",
        "room_rent_restriction",
    ]


def test_profile_surfaces_material_interaction_entries() -> None:
    interaction = BenefitInteractionReference(
        target_dimension_id="restoration",
        interaction_type=InteractionType.MAY_REDUCE_EFFECT,
        severity=InteractionSeverity.CRITICAL,
        explanation="Room-rent-linked proportionate deduction may reduce practical restoration effect.",
        source_mechanic_ids=("room_rent_limit", "proportionate_deduction"),
        evidence_reference_ids=("evidence:room-rent",),
    )
    room_rent = assessment(
        assessment_id="a-room-rent",
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_RESTRICTIVE,
        interactions=(interaction,),
    )
    result = profile(entry(room_rent))

    assert result.material_interaction_entries[0].assessment.dimension_id == (
        "room_rent_restriction"
    )


def test_profile_orders_dimensions_deterministically() -> None:
    restoration = assessment(
        assessment_id="a-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    copay = assessment(
        assessment_id="a-copay",
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.RESTRICTIVE,
    )
    result = profile(entry(restoration), entry(copay))
    assert [item.assessment.dimension_id for item in result.entries] == [
        "copayment",
        "restoration",
    ]


def test_profile_rejects_entry_bound_to_different_product() -> None:
    restoration = assessment(
        assessment_id="a-restoration",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    wrong = entry(
        restoration,
        product_reference="star_health:star_comprehensive:variant:SHAHLIP26044V092526",
    )
    with pytest.raises(ProductAssessmentProfileError, match="exact product reference"):
        profile(wrong)


def test_profile_rejects_duplicate_dimensions() -> None:
    first = assessment(
        assessment_id="a-restoration-1",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    second = assessment(
        assessment_id="a-restoration-2",
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_STRONG,
    )
    with pytest.raises(ProductAssessmentProfileError, match="duplicate"):
        profile(entry(first), entry(second))


def test_entry_disposition_is_semantic_not_numeric() -> None:
    moderate = assessment(
        assessment_id="a-moderate",
        dimension_id="home_healthcare",
        role=DecisionRole.CONTEXT_DEPENDENT,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.MODERATE,
    )
    assert entry(moderate).disposition is ProfileDimensionDisposition.NEUTRAL
