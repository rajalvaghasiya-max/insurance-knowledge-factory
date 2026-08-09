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
from insurance_intelligence.decision_support.customer_context import (
    CustomerContextProvenance,
    CustomerPriority,
    PriorityImportance,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentError,
    DimensionAlignmentStatus,
    align_assessment_to_customer_priority,
)


def priority(*, dimension_id: str, provenance=CustomerContextProvenance.DECLARED):
    return CustomerPriority(
        priority_id=f"priority:{dimension_id}",
        dimension_id=dimension_id,
        importance=PriorityImportance.HIGH,
        provenance=provenance,
        raw_statement=f"{dimension_id} matters to me.",
    )


def assessment(
    *,
    dimension_id: str,
    role: DecisionRole,
    status: AssessmentStatus,
    band: AssessmentBand | None,
    interactions: tuple[BenefitInteractionReference, ...] = (),
):
    policy_id = None
    policy_version = None
    limitations = ()
    if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS}:
        policy_id = f"assessment_policy:health:{dimension_id}:v1"
        policy_version = "1.0"
    if status is AssessmentStatus.ASSESSED_WITH_LIMITATIONS:
        limitations = ("Governed limitation remains visible.",)
    elif status is AssessmentStatus.NOT_SCORABLE:
        limitations = ("Required governed mechanic remains unresolved.",)

    return BenefitAssessment(
        assessment_id=f"assessment:{dimension_id}",
        implementation_id=f"implementation:{dimension_id}",
        concept_id=f"health:test:{dimension_id}",
        dimension_id=dimension_id,
        decision_role=role,
        status=status,
        assessment_band=band,
        assessment_policy_id=policy_id,
        assessment_policy_version=policy_version,
        summary=f"Summary for {dimension_id}",
        practical_meaning=f"Meaning for {dimension_id}",
        source_mechanic_ids=(f"mechanic:{dimension_id}",),
        evidence_reference_ids=(f"evidence:{dimension_id}",),
        limitations=limitations,
        interaction_references=interactions,
    )


def align(item, customer_priority):
    return align_assessment_to_customer_priority(
        finding_id=f"finding:{item.dimension_id}",
        product_reference="test_insurer:test_product:test_variant:TESTUIN",
        assessment=item,
        customer_priority=customer_priority,
    )


def test_very_strong_locally_strongly_aligns_with_declared_priority() -> None:
    item = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.VERY_STRONG,
    )
    result = align(item, priority(dimension_id="restoration"))
    assert result.status is DimensionAlignmentStatus.STRONGLY_ALIGNS


def test_restrictive_locally_conflicts_with_declared_priority() -> None:
    item = assessment(
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.RESTRICTIVE,
    )
    result = align(item, priority(dimension_id="copayment"))
    assert result.status is DimensionAlignmentStatus.CONFLICTS


def test_unresolved_assessment_never_produces_alignment_conclusion() -> None:
    item = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.NOT_SCORABLE,
        band=None,
    )
    result = align(item, priority(dimension_id="room_rent_restriction"))
    assert result.status is DimensionAlignmentStatus.UNRESOLVED


def test_inferred_priority_must_be_confirmed_before_alignment() -> None:
    item = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    with pytest.raises(DimensionAlignmentError, match="confirmed"):
        align(item, priority(
            dimension_id="restoration",
            provenance=CustomerContextProvenance.INFERRED,
        ))


def test_protection_floor_remains_visible_without_declared_priority() -> None:
    item = assessment(
        dimension_id="copayment",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.RESTRICTIVE,
    )
    result = align(item, None)
    assert result.status is DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED
    assert "must not be suppressed" in result.explanation


def test_non_protection_dimension_without_priority_has_no_local_alignment() -> None:
    item = assessment(
        dimension_id="ayush",
        role=DecisionRole.PREFERENCE,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    result = align(item, None)
    assert result.status is DimensionAlignmentStatus.NO_DECLARED_PRIORITY


def test_material_interaction_is_preserved_and_blocks_independent_interpretation() -> None:
    interaction = BenefitInteractionReference(
        target_dimension_id="restoration",
        interaction_type=InteractionType.MAY_REDUCE_EFFECT,
        severity=InteractionSeverity.CRITICAL,
        explanation="Proportionate deduction may reduce practical restoration effect.",
        source_mechanic_ids=("room_rent_limit", "proportionate_deduction"),
        evidence_reference_ids=("evidence:room-rent",),
    )
    item = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        status=AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
        band=AssessmentBand.VERY_RESTRICTIVE,
        interactions=(interaction,),
    )
    result = align(item, priority(dimension_id="room_rent_restriction"))

    assert result.interaction_references == (interaction,)
    assert result.has_material_interaction is True
    assert any("must not be interpreted independently" in x for x in result.limitations)


def test_priority_dimension_must_match_assessment_dimension() -> None:
    item = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    with pytest.raises(DimensionAlignmentError, match="same dimension"):
        align(item, priority(dimension_id="copayment"))


def test_alignment_contract_has_no_aggregate_verdict_fields() -> None:
    item = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        band=AssessmentBand.STRONG,
    )
    result = align(item, priority(dimension_id="restoration"))
    forbidden = {
        "score",
        "weight",
        "overall_score",
        "lean",
        "winner",
        "recommendation",
        "suitability",
        "rank",
    }
    assert forbidden.isdisjoint(result.__dataclass_fields__)
