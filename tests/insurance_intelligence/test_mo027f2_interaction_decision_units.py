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
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentFinding,
    DimensionAlignmentStatus,
)
from insurance_intelligence.decision_support.interaction_clusters import (
    InteractionClusterError,
    InteractionDecisionUnitStatus,
    build_interaction_decision_units,
)


PRODUCT_REFERENCE = "test_insurer:test_product:test_variant:TESTUIN"


def assessment(
    *,
    dimension_id: str,
    role: DecisionRole,
    interactions: tuple[BenefitInteractionReference, ...] = (),
) -> BenefitAssessment:
    return BenefitAssessment(
        assessment_id=f"assessment:{dimension_id}",
        implementation_id=f"implementation:{dimension_id}",
        concept_id=f"health:test:{dimension_id}",
        dimension_id=dimension_id,
        decision_role=role,
        status=AssessmentStatus.ASSESSED,
        assessment_band=AssessmentBand.STRONG,
        assessment_policy_id=f"policy:{dimension_id}",
        assessment_policy_version="1.0",
        summary=f"Summary for {dimension_id}",
        practical_meaning=f"Meaning for {dimension_id}",
        source_mechanic_ids=(f"mechanic:{dimension_id}",),
        evidence_reference_ids=(f"evidence:{dimension_id}",),
        interaction_references=interactions,
    )


def finding(item: BenefitAssessment) -> DimensionAlignmentFinding:
    return DimensionAlignmentFinding(
        finding_id=f"finding:{item.dimension_id}",
        product_reference=PRODUCT_REFERENCE,
        dimension_id=item.dimension_id,
        decision_role=item.decision_role,
        assessment=item,
        customer_priority=None,
        status=(
            DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED
            if item.decision_role is DecisionRole.PROTECTION_FLOOR
            else DimensionAlignmentStatus.NO_DECLARED_PRIORITY
        ),
        explanation=f"Local finding for {item.dimension_id}",
        interaction_references=item.interaction_references,
    )


def material_link(target: str, *, severity: InteractionSeverity = InteractionSeverity.MATERIAL):
    return BenefitInteractionReference(
        target_dimension_id=target,
        interaction_type=InteractionType.MAY_REDUCE_EFFECT,
        severity=severity,
        explanation=f"May affect {target}",
        source_mechanic_ids=("room_rent_limit", "proportionate_deduction"),
        evidence_reference_ids=("evidence:room-rent",),
    )


def test_material_interaction_groups_findings_into_one_decision_unit() -> None:
    room = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        interactions=(material_link("restoration", severity=InteractionSeverity.CRITICAL),),
    )
    restoration = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
    )

    units = build_interaction_decision_units(
        product_reference=PRODUCT_REFERENCE,
        findings=(finding(restoration), finding(room)),
    )

    assert len(units) == 1
    unit = units[0]
    assert unit.status is InteractionDecisionUnitStatus.COMPLETE
    assert unit.dimension_ids == ("restoration", "room_rent_restriction")
    assert [item.dimension_id for item in unit.findings] == [
        "restoration",
        "room_rent_restriction",
    ]
    assert unit.missing_linked_dimension_ids == ()


def test_missing_linked_dimension_is_explicitly_incomplete() -> None:
    room = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        interactions=(material_link("restoration"),),
    )

    unit = build_interaction_decision_units(
        product_reference=PRODUCT_REFERENCE,
        findings=(finding(room),),
    )[0]

    assert unit.status is InteractionDecisionUnitStatus.INCOMPLETE_LINKED_DIMENSION
    assert unit.dimension_ids == ("restoration", "room_rent_restriction")
    assert unit.missing_linked_dimension_ids == ("restoration",)
    assert "must not be interpreted independently" in unit.explanation.lower()


def test_informational_interaction_does_not_create_decision_unit() -> None:
    room = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        interactions=(
            material_link("restoration", severity=InteractionSeverity.INFORMATIONAL),
        ),
    )
    restoration = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
    )

    assert build_interaction_decision_units(
        product_reference=PRODUCT_REFERENCE,
        findings=(finding(room), finding(restoration)),
    ) == ()


def test_transitive_material_links_form_single_connected_unit() -> None:
    room = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        interactions=(material_link("restoration"),),
    )
    restoration = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
        interactions=(
            BenefitInteractionReference(
                target_dimension_id="sum_insured",
                interaction_type=InteractionType.DEPENDS_ON,
                severity=InteractionSeverity.MATERIAL,
                explanation="Restoration depends on usable sum insured mechanics.",
                source_mechanic_ids=("restoration_trigger",),
                evidence_reference_ids=("evidence:restoration",),
            ),
        ),
    )
    si = assessment(
        dimension_id="sum_insured",
        role=DecisionRole.CORE_PROTECTION,
    )

    unit = build_interaction_decision_units(
        product_reference=PRODUCT_REFERENCE,
        findings=(finding(si), finding(room), finding(restoration)),
    )[0]

    assert unit.dimension_ids == (
        "restoration",
        "room_rent_restriction",
        "sum_insured",
    )
    assert unit.status is InteractionDecisionUnitStatus.COMPLETE


def test_unrelated_findings_are_not_forced_into_interaction_unit() -> None:
    room = assessment(
        dimension_id="room_rent_restriction",
        role=DecisionRole.PROTECTION_FLOOR,
        interactions=(material_link("restoration"),),
    )
    restoration = assessment(
        dimension_id="restoration",
        role=DecisionRole.CORE_PROTECTION,
    )
    ayush = assessment(
        dimension_id="ayush",
        role=DecisionRole.PREFERENCE,
    )

    unit = build_interaction_decision_units(
        product_reference=PRODUCT_REFERENCE,
        findings=(finding(ayush), finding(room), finding(restoration)),
    )[0]

    assert "ayush" not in unit.dimension_ids


def test_findings_from_different_product_are_rejected() -> None:
    room = finding(
        assessment(
            dimension_id="room_rent_restriction",
            role=DecisionRole.PROTECTION_FLOOR,
            interactions=(material_link("restoration"),),
        )
    )
    foreign = DimensionAlignmentFinding(
        finding_id="foreign:restoration",
        product_reference="other:product:variant:uin",
        dimension_id="restoration",
        decision_role=DecisionRole.CORE_PROTECTION,
        assessment=assessment(
            dimension_id="restoration",
            role=DecisionRole.CORE_PROTECTION,
        ),
        customer_priority=None,
        status=DimensionAlignmentStatus.NO_DECLARED_PRIORITY,
        explanation="Foreign product finding",
        interaction_references=(),
    )

    with pytest.raises(InteractionClusterError, match="product_reference"):
        build_interaction_decision_units(
            product_reference=PRODUCT_REFERENCE,
            findings=(room, foreign),
        )


def test_decision_unit_has_no_aggregate_verdict_fields() -> None:
    from insurance_intelligence.decision_support.interaction_clusters import (
        InteractionDecisionUnit,
    )

    forbidden = {
        "score",
        "overall_score",
        "weight",
        "winner",
        "lean",
        "recommendation",
        "suitability",
        "claim_admissibility",
    }
    assert forbidden.isdisjoint(InteractionDecisionUnit.__dataclass_fields__)
