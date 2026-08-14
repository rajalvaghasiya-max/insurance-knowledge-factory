from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.comparison_projection_assessment_bridge import (
    assessment_from_comparison_projection,
)
from insurance_intelligence.decision_support.decision_projection import (
    DecisionProjectionStatus,
    project_decision_support,
)
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyStatus,
    ProductDecisionEvidence,
    evaluate_decision_sufficiency,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentStatus,
    align_assessment_to_customer_priority,
)
from insurance_intelligence.generic_knowledge.contracts import AccountingState, ApplicabilityKey
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_comparison_projection import (
    project_waiting_period_dimension,
)


LEFT_REF = "insurer_a:product_a:base:uin_a"
RIGHT_REF = "insurer_b:product_b:base:uin_b"


def _assessed_left() -> BenefitAssessment:
    return BenefitAssessment(
        assessment_id="assessment-left-ped",
        implementation_id="impl-left-ped",
        concept_id="health:waiting_period:ped",
        dimension_id="ped_waiting_period",
        decision_role=DecisionRole.CORE_PROTECTION,
        status=AssessmentStatus.ASSESSED,
        assessment_band=AssessmentBand.STRONG,
        assessment_policy_id="policy-common",
        assessment_policy_version="1.0",
        summary="Governed assessment.",
        practical_meaning="Governed comparison-ready assessment.",
        source_mechanic_ids=("wp-left",),
        evidence_reference_ids=("ev-left-ped",),
    )


def test_policy_schedule_bound_remains_action_required_in_decision_projection() -> None:
    right_projection = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_waiting_period",
        applicability=ApplicabilityKey(product_reference=RIGHT_REF, policy_version="v1"),
        evidence_ids=("ev-right-ped",),
        accounting_state=AccountingState.MAPPED,
        resolution=compute_resolution_status(
            ResolutionInputs(
                value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
                instance_availability=InstanceAvailability.MISSING,
            )
        ),
        structured_value=None,
    )
    right_assessment = assessment_from_comparison_projection(
        projection=right_projection,
        implementation_id="impl-right-ped",
        decision_role=DecisionRole.CORE_PROTECTION,
        source_mechanic_ids=("wp-right",),
    )
    left_assessment = _assessed_left()

    left_alignment = align_assessment_to_customer_priority(
        finding_id="finding-left-ped",
        product_reference=LEFT_REF,
        assessment=left_assessment,
        customer_priority=None,
    )
    right_alignment = align_assessment_to_customer_priority(
        finding_id="finding-right-ped",
        product_reference=RIGHT_REF,
        assessment=right_assessment,
        customer_priority=None,
    )
    assert right_alignment.status is DimensionAlignmentStatus.UNRESOLVED

    left_evidence = ProductDecisionEvidence(
        product_reference=LEFT_REF,
        alignments=(left_alignment,),
    )
    right_evidence = ProductDecisionEvidence(
        product_reference=RIGHT_REF,
        alignments=(right_alignment,),
    )
    sufficiency = evaluate_decision_sufficiency(
        decision_id="decision-ped",
        left=left_evidence,
        right=right_evidence,
    )
    assert sufficiency.status is DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN
    assert sufficiency.blocking_reference_ids == ("finding-right-ped",)

    projection = project_decision_support(
        projection_id="decision-projection-ped",
        sufficiency=sufficiency,
        left=left_evidence,
        right=right_evidence,
    )
    assert projection.status is DecisionProjectionStatus.ACTION_REQUIRED
    assert projection.right.unresolved_findings == (right_alignment,)
    assert projection.blocking_reference_ids == ("finding-right-ped",)
    assert projection.left.unresolved_findings == ()
    assert "does not choose" in projection.decision_boundary.lower()
