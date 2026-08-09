from dataclasses import replace

import pytest

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
from insurance_intelligence.decision_support.decision_projection import (
    DecisionProjectionError,
    DecisionProjectionStatus,
    GovernedDecisionSupportProjection,
    project_decision_support,
)
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyStatus,
    ProductConstraintStatus,
    ProductDecisionEvidence,
    evaluate_decision_sufficiency,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    align_assessment_to_customer_priority,
)


LEFT = "insurer_a:plan_a:variant_a:UINA"
RIGHT = "insurer_b:plan_b:variant_b:UINB"


def assessment(dimension_id: str, role: DecisionRole, band: AssessmentBand):
    return BenefitAssessment(
        assessment_id=f"assessment:{dimension_id}",
        implementation_id=f"implementation:{dimension_id}",
        concept_id=f"health:test:{dimension_id}",
        dimension_id=dimension_id,
        decision_role=role,
        status=AssessmentStatus.ASSESSED,
        assessment_band=band,
        assessment_policy_id=f"policy:{dimension_id}",
        assessment_policy_version="1.0",
        summary=f"Summary {dimension_id}",
        practical_meaning=f"Meaning {dimension_id}",
        source_mechanic_ids=(f"mechanic:{dimension_id}",),
        evidence_reference_ids=(f"evidence:{dimension_id}",),
    )


def priority(dimension_id: str):
    return CustomerPriority(
        priority_id=f"priority:{dimension_id}",
        dimension_id=dimension_id,
        importance=PriorityImportance.HIGH,
        provenance=CustomerContextProvenance.DECLARED,
        raw_statement=f"{dimension_id} matters to me.",
    )


def finding(product: str, dimension_id: str, role: DecisionRole, band: AssessmentBand, *, with_priority=True):
    item = assessment(dimension_id, role, band)
    return align_assessment_to_customer_priority(
        finding_id=f"finding:{product}:{dimension_id}",
        product_reference=product,
        assessment=item,
        customer_priority=priority(dimension_id) if with_priority else None,
    )


def evidence(product: str, *, restrictive_floor=False, fail_constraint=False):
    restoration = finding(product, "restoration", DecisionRole.CORE_PROTECTION, AssessmentBand.STRONG)
    copay = finding(
        product,
        "copayment",
        DecisionRole.PROTECTION_FLOOR,
        AssessmentBand.RESTRICTIVE if restrictive_floor else AssessmentBand.VERY_STRONG,
        with_priority=False,
    )
    return ProductDecisionEvidence(
        product_reference=product,
        alignments=(copay, restoration),
        constraint_status=(
            ProductConstraintStatus.FAILS_ONE_OR_MORE
            if fail_constraint
            else ProductConstraintStatus.SATISFIES_ALL
        ),
        failed_constraint_ids=("constraint:premium",) if fail_constraint else (),
    )


def project(left=None, right=None, *, pending=(), signals=()):
    left = left or evidence(LEFT)
    right = right or evidence(RIGHT)
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:test",
        left=left,
        right=right,
        pending_material_question_ids=pending,
        set_adequacy_signals=signals,
    )
    return project_decision_support(
        projection_id="projection:test",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )


def test_ready_projection_is_set_relative_and_non_verdict() -> None:
    result = project()
    assert result.status is DecisionProjectionStatus.READY_WITH_LIMITATIONS
    assert "among the compared products" in result.set_scope_statement.lower()
    assert "does not choose" in result.decision_boundary.lower()
    assert "user decides" in result.decision_boundary.lower()


def test_protection_floor_findings_cannot_disappear_from_projection() -> None:
    result = project()
    assert [x.dimension_id for x in result.left.protection_floor_findings] == ["copayment"]
    assert result.left.protection_floor_findings[0] is result.left.alignments[0]


def test_both_material_concerns_project_as_limitations_not_winner() -> None:
    result = project(evidence(LEFT, restrictive_floor=True), evidence(RIGHT, restrictive_floor=True))
    assert result.status is DecisionProjectionStatus.READY_WITH_LIMITATIONS
    assert any("Both compared products" in reason for reason in result.limitations)


def test_pending_material_question_projects_action_required() -> None:
    result = project(pending=("question:claim-time-cost",))
    assert result.status is DecisionProjectionStatus.ACTION_REQUIRED
    assert result.blocking_reference_ids == ("question:claim-time-cost",)


def test_neither_meets_hard_constraints_preserves_failures_without_selecting_product() -> None:
    left = evidence(LEFT, fail_constraint=True)
    right = evidence(RIGHT, fail_constraint=True)
    result = project(left, right)
    assert result.status is DecisionProjectionStatus.ACTION_REQUIRED
    assert result.left.failed_constraint_ids == ("constraint:premium",)
    assert result.right.failed_constraint_ids == ("constraint:premium",)
    assert "Neither compared product" in result.limitations[0]


def test_sufficiency_product_identity_must_match_projection_inputs() -> None:
    left = evidence(LEFT)
    right = evidence(RIGHT)
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:test",
        left=left,
        right=right,
    )
    with pytest.raises(DecisionProjectionError, match="left product"):
        project_decision_support(
            projection_id="projection:test",
            sufficiency=sufficiency,
            left=evidence("other:product:variant:UINX"),
            right=right,
        )


def test_decision_boundary_rejects_soft_verdict_language() -> None:
    result = project()
    with pytest.raises(DecisionProjectionError, match="verdict language"):
        replace(result, decision_boundary="Plan B leans toward being the better choice; the user decides.")


def test_projection_contract_has_no_aggregate_verdict_fields() -> None:
    forbidden = {
        "score",
        "weight",
        "overall_score",
        "lean",
        "winner",
        "recommendation",
        "suitability",
        "rank",
        "preferred_product",
    }
    assert forbidden.isdisjoint(GovernedDecisionSupportProjection.__dataclass_fields__)
