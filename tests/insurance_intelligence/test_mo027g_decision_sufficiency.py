from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.decision_support.customer_context import (
    CustomerContextProvenance,
    CustomerPriority,
    PriorityImportance,
)
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyStatus,
    ProductConstraintStatus,
    ProductDecisionEvidence,
    SetAdequacySignal,
    evaluate_decision_sufficiency,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    align_assessment_to_customer_priority,
)


LEFT = "insurer_a:product_a:variant_a:UINA"
RIGHT = "insurer_b:product_b:variant_b:UINB"


def priority(dimension_id: str):
    return CustomerPriority(
        priority_id=f"priority:{dimension_id}",
        dimension_id=dimension_id,
        importance=PriorityImportance.HIGH,
        provenance=CustomerContextProvenance.DECLARED,
        raw_statement=f"{dimension_id} matters to me.",
    )


def alignment(*, product_reference: str, dimension_id: str, role: DecisionRole, band: AssessmentBand | None, status=AssessmentStatus.ASSESSED):
    limitations = ()
    policy_id = f"policy:{dimension_id}:v1" if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS} else None
    policy_version = "1.0" if policy_id else None
    if status is AssessmentStatus.NOT_SCORABLE:
        limitations = ("Governed mechanic unresolved.",)
    assessment = BenefitAssessment(
        assessment_id=f"assessment:{product_reference}:{dimension_id}",
        implementation_id=f"impl:{product_reference}:{dimension_id}",
        concept_id=f"health:test:{dimension_id}",
        dimension_id=dimension_id,
        decision_role=role,
        status=status,
        assessment_band=band,
        assessment_policy_id=policy_id,
        assessment_policy_version=policy_version,
        summary=f"Summary {dimension_id}",
        practical_meaning=f"Meaning {dimension_id}",
        source_mechanic_ids=(f"mechanic:{dimension_id}",),
        evidence_reference_ids=(f"evidence:{dimension_id}",),
        limitations=limitations,
    )
    return align_assessment_to_customer_priority(
        finding_id=f"finding:{product_reference}:{dimension_id}",
        product_reference=product_reference,
        assessment=assessment,
        customer_priority=priority(dimension_id),
    )


def evidence(product_reference: str, *items, constraint_status=ProductConstraintStatus.SATISFIES_ALL, failed=()):
    return ProductDecisionEvidence(
        product_reference=product_reference,
        alignments=tuple(items),
        constraint_status=constraint_status,
        failed_constraint_ids=tuple(failed),
    )


def test_ready_when_governed_context_is_sufficient_and_non_verdict() -> None:
    left = evidence(LEFT, alignment(product_reference=LEFT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.STRONG))
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.VERY_STRONG))
    result = evaluate_decision_sufficiency(decision_id="d1", left=left, right=right)
    assert result.status is DecisionSufficiencyStatus.DECISION_SUPPORT_READY
    forbidden = {"winner", "recommendation", "suitability", "score", "weight", "lean", "rank"}
    assert forbidden.isdisjoint(result.__dataclass_fields__)


def test_pending_material_questions_require_more_customer_context() -> None:
    left = evidence(LEFT, alignment(product_reference=LEFT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.STRONG))
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.STRONG))
    result = evaluate_decision_sufficiency(
        decision_id="d2", left=left, right=right, pending_material_question_ids=("question:copay",)
    )
    assert result.status is DecisionSufficiencyStatus.MORE_CUSTOMER_CONTEXT_REQUIRED
    assert result.blocking_reference_ids == ("question:copay",)


def test_product_unknown_blocks_decision_support() -> None:
    left = evidence(LEFT, alignment(product_reference=LEFT, dimension_id="room_rent_restriction", role=DecisionRole.PROTECTION_FLOOR, band=None, status=AssessmentStatus.NOT_SCORABLE))
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="room_rent_restriction", role=DecisionRole.PROTECTION_FLOOR, band=AssessmentBand.VERY_STRONG))
    result = evaluate_decision_sufficiency(decision_id="d3", left=left, right=right)
    assert result.status is DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN


def test_neither_product_meeting_hard_constraints_is_first_class_outcome() -> None:
    left = evidence(
        LEFT,
        alignment(product_reference=LEFT, dimension_id="quoted_premium", role=DecisionRole.PRICE, band=AssessmentBand.MODERATE),
        constraint_status=ProductConstraintStatus.FAILS_ONE_OR_MORE,
        failed=("constraint:budget",),
    )
    right = evidence(
        RIGHT,
        alignment(product_reference=RIGHT, dimension_id="quoted_premium", role=DecisionRole.PRICE, band=AssessmentBand.MODERATE),
        constraint_status=ProductConstraintStatus.FAILS_ONE_OR_MORE,
        failed=("constraint:budget",),
    )
    result = evaluate_decision_sufficiency(decision_id="d4", left=left, right=right)
    assert result.status is DecisionSufficiencyStatus.NEITHER_MEETS_HARD_CONSTRAINTS
    assert result.blocking_reference_ids == ("constraint:budget",)


def test_shared_set_weakness_marks_set_may_be_inadequate() -> None:
    left = evidence(LEFT, alignment(product_reference=LEFT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.STRONG))
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="restoration", role=DecisionRole.CORE_PROTECTION, band=AssessmentBand.STRONG))
    result = evaluate_decision_sufficiency(
        decision_id="d5",
        left=left,
        right=right,
        set_adequacy_signals=(SetAdequacySignal.SHARED_MATERIAL_WEAKNESS,),
    )
    assert result.status is DecisionSufficiencyStatus.SET_MAY_BE_INADEQUATE


def test_both_products_with_material_conflicts_are_not_forced_into_a_winner() -> None:
    left = evidence(LEFT, alignment(product_reference=LEFT, dimension_id="copayment", role=DecisionRole.PROTECTION_FLOOR, band=AssessmentBand.RESTRICTIVE))
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="room_rent_restriction", role=DecisionRole.PROTECTION_FLOOR, band=AssessmentBand.VERY_RESTRICTIVE))
    result = evaluate_decision_sufficiency(decision_id="d6", left=left, right=right)
    assert result.status is DecisionSufficiencyStatus.BOTH_HAVE_MATERIAL_CONCERNS


def test_one_product_failing_constraint_does_not_become_an_automatic_winner_for_other() -> None:
    left = evidence(
        LEFT,
        alignment(product_reference=LEFT, dimension_id="quoted_premium", role=DecisionRole.PRICE, band=AssessmentBand.MODERATE),
        constraint_status=ProductConstraintStatus.FAILS_ONE_OR_MORE,
        failed=("constraint:budget",),
    )
    right = evidence(RIGHT, alignment(product_reference=RIGHT, dimension_id="quoted_premium", role=DecisionRole.PRICE, band=AssessmentBand.MODERATE))
    result = evaluate_decision_sufficiency(decision_id="d7", left=left, right=right)
    assert result.status is DecisionSufficiencyStatus.DECISION_SUPPORT_READY
    assert "winner" not in " ".join(result.reasons).lower()


def test_status_contract_has_no_net_direction_fields() -> None:
    forbidden = {"winner", "recommended_product", "preferred_product", "net_direction", "lean", "score", "weight", "rank"}
    assert forbidden.isdisjoint(ProductDecisionEvidence.__dataclass_fields__)
