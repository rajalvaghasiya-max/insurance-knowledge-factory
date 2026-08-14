from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.comparison_projection_assessment_bridge import (
    ComparisonProjectionAssessmentBridgeError,
    assessment_from_comparison_projection,
)
from insurance_intelligence.benefits.product_assessment_profile import (
    ProductAssessmentEntry,
    build_product_assessment_profile,
)
from insurance_intelligence.benefits.tradeoff_comparison import (
    DimensionTradeoffStatus,
    compare_product_assessment_profiles,
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
from insurance_intelligence.generic_knowledge.benefit_limit_applicability import (
    BenefitLimitApplicability,
    BenefitLimitApplicabilityCell,
)
from insurance_intelligence.generic_knowledge.benefit_limit_comparison_projection import (
    project_benefit_limit_dimension,
)
from insurance_intelligence.generic_knowledge.benefit_limit_contracts import (
    BenefitIdentityReference,
    BenefitLimitMechanic,
    CostSharingApplicability,
    CostSharingInteractionRule,
    CostSharingMechanicType,
    CostSharingOrdering,
    EventScope,
    LimitKind,
    MonetaryAmount,
    TimeScope,
)
from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    NotComparableDimension,
)
from insurance_intelligence.generic_knowledge.contracts import (
    AccountingState,
    ApplicabilityKey,
    EvidenceReference,
)
from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    ResolutionInputs,
    ResolutionStatus,
    ValueSource,
    compute_resolution_status,
)
from insurance_intelligence.generic_knowledge.waiting_period_comparison_projection import (
    project_waiting_period_dimension,
)

import pytest


LEFT_REF = "insurer_a:product_a:base:uin_a"
RIGHT_REF = "insurer_b:product_b:base:uin_b"


def _app(product_reference: str) -> ApplicabilityKey:
    return ApplicabilityKey(product_reference=product_reference, policy_version="v1")


def _evidence(evidence_id: str) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        source_document_id=f"doc-{evidence_id}",
        source_document_version="v1",
        source_hash_sha256=f"sha-{evidence_id}",
        locator="page:1",
        authority_class="POLICY_WORDING",
    )


def _assessed(
    *,
    implementation_id: str,
    concept_id: str,
    dimension_id: str,
    evidence_ids: tuple[str, ...],
    role: DecisionRole,
    band: AssessmentBand = AssessmentBand.STRONG,
) -> BenefitAssessment:
    return BenefitAssessment(
        assessment_id=f"assessment-{implementation_id}-{dimension_id}",
        implementation_id=implementation_id,
        concept_id=concept_id,
        dimension_id=dimension_id,
        decision_role=role,
        status=AssessmentStatus.ASSESSED,
        assessment_band=band,
        assessment_policy_id="policy-common",
        assessment_policy_version="1.0",
        summary="Governed assessment.",
        practical_meaning="Governed comparison-ready assessment.",
        source_mechanic_ids=(f"mechanic-{implementation_id}-{dimension_id}",),
        evidence_reference_ids=evidence_ids,
    )


def _profile(*, side: str, assessment: BenefitAssessment):
    if side == "left":
        insurer, product, variant, uin, ref = "insurer_a", "product_a", "base", "uin_a", LEFT_REF
    else:
        insurer, product, variant, uin, ref = "insurer_b", "product_b", "base", "uin_b", RIGHT_REF
    return build_product_assessment_profile(
        profile_id=f"profile-{side}",
        insurer_id=insurer,
        product_id=product,
        product_variant_id=variant,
        product_uin=uin,
        entries=(ProductAssessmentEntry(product_reference=ref, assessment=assessment),),
    )


def _assert_downstream_blocks_directional_advantage(
    *, left_assessment: BenefitAssessment, right_assessment: BenefitAssessment
) -> None:
    left_profile = _profile(side="left", assessment=left_assessment)
    right_profile = _profile(side="right", assessment=right_assessment)

    comparison = compare_product_assessment_profiles(
        comparison_id="comparison-adversarial",
        left=left_profile,
        right=right_profile,
    )
    assert len(comparison.dimensions) == 1
    tradeoff = comparison.dimensions[0]
    assert tradeoff.status is DimensionTradeoffStatus.UNRESOLVED
    assert comparison.left_stronger_dimensions == ()
    assert comparison.right_stronger_dimensions == ()

    left_alignment = align_assessment_to_customer_priority(
        finding_id="finding-left",
        product_reference=LEFT_REF,
        assessment=left_assessment,
        customer_priority=None,
    )
    right_alignment = align_assessment_to_customer_priority(
        finding_id="finding-right",
        product_reference=RIGHT_REF,
        assessment=right_assessment,
        customer_priority=None,
    )
    assert right_alignment.status is DimensionAlignmentStatus.UNRESOLVED

    decision = evaluate_decision_sufficiency(
        decision_id="decision-adversarial",
        left=ProductDecisionEvidence(
            product_reference=LEFT_REF,
            alignments=(left_alignment,),
        ),
        right=ProductDecisionEvidence(
            product_reference=RIGHT_REF,
            alignments=(right_alignment,),
        ),
    )
    assert decision.status is DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN


def test_waiting_period_schedule_bound_cannot_become_favorable_downstream() -> None:
    concept_id = "health:waiting_period:ped"
    dimension_id = "ped_waiting_period"
    left_resolution = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    right_resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assert left_resolution.status is ResolutionStatus.RESOLVED
    assert right_resolution.status is ResolutionStatus.POLICY_SCHEDULE_BOUND

    left_projection = project_waiting_period_dimension(
        concept_id=concept_id,
        dimension_id=dimension_id,
        applicability=_app(LEFT_REF),
        evidence_ids=("ev-left-wp",),
        accounting_state=AccountingState.MAPPED,
        resolution=left_resolution,
        structured_value={"duration": 36, "unit": "MONTHS"},
    )
    right_projection = project_waiting_period_dimension(
        concept_id=concept_id,
        dimension_id=dimension_id,
        applicability=_app(RIGHT_REF),
        evidence_ids=("ev-right-wp",),
        accounting_state=AccountingState.MAPPED,
        resolution=right_resolution,
        structured_value=None,
    )
    assert isinstance(left_projection, ComparableDimension)
    assert isinstance(right_projection, NotComparableDimension)

    left_assessment = assessment_from_comparison_projection(
        projection=left_projection,
        implementation_id="impl-left-wp",
        decision_role=DecisionRole.CORE_PROTECTION,
        source_mechanic_ids=("wp-left",),
        comparable_assessment=_assessed(
            implementation_id="impl-left-wp",
            concept_id=concept_id,
            dimension_id=dimension_id,
            evidence_ids=left_projection.evidence_ids,
            role=DecisionRole.CORE_PROTECTION,
        ),
    )
    right_assessment = assessment_from_comparison_projection(
        projection=right_projection,
        implementation_id="impl-right-wp",
        decision_role=DecisionRole.CORE_PROTECTION,
        source_mechanic_ids=("wp-right",),
    )
    assert right_assessment.status is AssessmentStatus.NOT_SCORABLE
    assert right_assessment.assessment_band is None
    _assert_downstream_blocks_directional_advantage(
        left_assessment=left_assessment,
        right_assessment=right_assessment,
    )


def _limit_cell(
    *, product_reference: str, evidence_id: str, ordering: CostSharingOrdering
) -> BenefitLimitApplicabilityCell:
    evidence = _evidence(evidence_id)
    mechanic = BenefitLimitMechanic(
        benefit_identity=BenefitIdentityReference(
            concept_id="health:benefit:cataract",
            alias_registry_version="v1",
            alias_registry_snapshot_id="snapshot-1",
        ),
        limit_kind=LimitKind.FIXED_CURRENCY,
        ontology_version="1.0",
        core_evidence_references=(evidence,),
        amount=MonetaryAmount(40000),
        time_scope=TimeScope.PER_POLICY_YEAR,
        event_scope=EventScope.PER_EYE,
        scope_evidence_references=(evidence,),
        cost_sharing_interactions=(
            CostSharingInteractionRule(
                mechanic_type=CostSharingMechanicType.COPAY,
                applies=CostSharingApplicability.YES,
                ordering=ordering,
                evidence_references=(evidence,),
            ),
        ),
    )
    return BenefitLimitApplicabilityCell(
        mechanic=mechanic,
        applicability=BenefitLimitApplicability(
            base_applicability=_app(product_reference)
        ),
    )


def test_unknown_benefit_limit_interaction_ordering_cannot_become_favorable_downstream() -> None:
    dimension_id = "cataract_limit"
    left_cell = _limit_cell(
        product_reference=LEFT_REF,
        evidence_id="ev-left-limit",
        ordering=CostSharingOrdering.AFTER_LIMIT,
    )
    right_cell = _limit_cell(
        product_reference=RIGHT_REF,
        evidence_id="ev-right-limit",
        ordering=CostSharingOrdering.UNKNOWN,
    )
    assert left_cell.mechanic.equivalence_ready is True
    assert right_cell.mechanic.equivalence_ready is False

    left_projection = project_benefit_limit_dimension(
        cell=left_cell,
        dimension_id=dimension_id,
        evidence_ids=("ev-left-limit",),
        accounting_state=AccountingState.MAPPED,
    )
    right_projection = project_benefit_limit_dimension(
        cell=right_cell,
        dimension_id=dimension_id,
        evidence_ids=("ev-right-limit",),
        accounting_state=AccountingState.MAPPED,
    )
    assert isinstance(left_projection, ComparableDimension)
    assert isinstance(right_projection, NotComparableDimension)

    left_assessment = assessment_from_comparison_projection(
        projection=left_projection,
        implementation_id="impl-left-limit",
        decision_role=DecisionRole.CORE_PROTECTION,
        source_mechanic_ids=("limit-left",),
        comparable_assessment=_assessed(
            implementation_id="impl-left-limit",
            concept_id="health:benefit:cataract",
            dimension_id=dimension_id,
            evidence_ids=left_projection.evidence_ids,
            role=DecisionRole.CORE_PROTECTION,
        ),
    )
    right_assessment = assessment_from_comparison_projection(
        projection=right_projection,
        implementation_id="impl-right-limit",
        decision_role=DecisionRole.CORE_PROTECTION,
        source_mechanic_ids=("limit-right",),
    )
    assert right_assessment.status is AssessmentStatus.NOT_SCORABLE
    assert "not equivalence-ready" in right_assessment.limitations[0]
    _assert_downstream_blocks_directional_advantage(
        left_assessment=left_assessment,
        right_assessment=right_assessment,
    )


def test_blocked_projection_rejects_favorable_assessment_passthrough() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    projection = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_waiting_period",
        applicability=_app(RIGHT_REF),
        evidence_ids=("ev-blocked",),
        accounting_state=AccountingState.MAPPED,
        resolution=resolution,
        structured_value=None,
    )
    favorable = _assessed(
        implementation_id="impl-blocked",
        concept_id="health:waiting_period:ped",
        dimension_id="ped_waiting_period",
        evidence_ids=("ev-blocked",),
        role=DecisionRole.CORE_PROTECTION,
        band=AssessmentBand.VERY_STRONG,
    )
    with pytest.raises(ComparisonProjectionAssessmentBridgeError):
        assessment_from_comparison_projection(
            projection=projection,
            implementation_id="impl-blocked",
            decision_role=DecisionRole.CORE_PROTECTION,
            source_mechanic_ids=("blocked-source",),
            comparable_assessment=favorable,
        )


def test_comparable_projection_requires_assessed_passthrough_with_matching_evidence() -> None:
    resolution = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    projection = project_waiting_period_dimension(
        concept_id="health:waiting_period:ped",
        dimension_id="ped_waiting_period",
        applicability=_app(LEFT_REF),
        evidence_ids=("ev-required",),
        accounting_state=AccountingState.MAPPED,
        resolution=resolution,
        structured_value={"duration": 36, "unit": "MONTHS"},
    )
    with pytest.raises(ComparisonProjectionAssessmentBridgeError):
        assessment_from_comparison_projection(
            projection=projection,
            implementation_id="impl-left",
            decision_role=DecisionRole.CORE_PROTECTION,
            source_mechanic_ids=("source-left",),
        )
