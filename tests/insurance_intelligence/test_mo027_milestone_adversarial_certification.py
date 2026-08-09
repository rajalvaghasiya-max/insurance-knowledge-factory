"""Milestone-level adversarial certification for MO-027 A->H.

These tests exercise composition invariants that are easy to miss when each slice is
correct in isolation. The certified default path must remain non-verdict, preserve
protection floors and unknowns, reject inferred customer inputs from material logic,
respect personalization isolation, and surface interaction/set adequacy blockers.
"""
from datetime import date

import pytest

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.decision_support.circumstance_relevance import (
    CircumstanceOperator,
    CircumstanceRelevanceError,
    CircumstanceRelevanceRule,
    CustomerCircumstanceFact,
    CustomerFactProvenance,
    RelevanceClaimType,
    RelevanceEffect,
    RelevanceRuleBasis,
    evaluate_circumstance_relevance,
)
from insurance_intelligence.decision_support.customer_context import (
    CustomerContextProvenance,
    CustomerPriority,
    PriorityImportance,
)
from insurance_intelligence.decision_support.decision_projection import (
    DecisionProjectionError,
    project_decision_support,
)
from insurance_intelligence.decision_support.decision_sufficiency import (
    DecisionSufficiencyStatus,
    ProductConstraintStatus,
    ProductDecisionEvidence,
    SetAdequacySignal,
    evaluate_decision_sufficiency,
)
from insurance_intelligence.decision_support.dimension_alignment import (
    DimensionAlignmentError,
    DimensionAlignmentStatus,
    align_assessment_to_customer_priority,
)
from insurance_intelligence.decision_support.personalization_boundary import (
    CustomerContextAccess,
    PersonalizationBoundaryState,
    PersonalizationState,
    TurnIntent,
    decide_personalization_boundary,
    next_boundary_state,
)


LEFT = "insurer_a:product_a:variant_a:UINA"
RIGHT = "insurer_b:product_b:variant_b:UINB"


def _assessment(product: str, dimension: str, role: DecisionRole, band: AssessmentBand | None, *, status=AssessmentStatus.ASSESSED):
    limitations = ()
    policy_id = f"policy:{dimension}:v1" if status in {AssessmentStatus.ASSESSED, AssessmentStatus.ASSESSED_WITH_LIMITATIONS} else None
    policy_version = "1.0" if policy_id else None
    if status is AssessmentStatus.NOT_SCORABLE:
        limitations = ("Governed product fact remains unresolved.",)
    return BenefitAssessment(
        assessment_id=f"assessment:{product}:{dimension}",
        implementation_id=f"implementation:{product}:{dimension}",
        concept_id=f"health:test:{dimension}",
        dimension_id=dimension,
        decision_role=role,
        status=status,
        assessment_band=band,
        assessment_policy_id=policy_id,
        assessment_policy_version=policy_version,
        summary=f"Summary for {dimension}",
        practical_meaning=f"Meaning for {dimension}",
        source_mechanic_ids=(f"mechanic:{dimension}",),
        evidence_reference_ids=(f"evidence:{product}:{dimension}",),
        limitations=limitations,
    )


def _priority(dimension: str, provenance=CustomerContextProvenance.DECLARED):
    return CustomerPriority(
        priority_id=f"priority:{dimension}",
        dimension_id=dimension,
        importance=PriorityImportance.HIGH,
        provenance=provenance,
        raw_statement=f"{dimension} matters to me.",
    )


def _alignment(product: str, dimension: str, role: DecisionRole, band: AssessmentBand | None, *, priority=True, status=AssessmentStatus.ASSESSED):
    return align_assessment_to_customer_priority(
        finding_id=f"finding:{product}:{dimension}",
        product_reference=product,
        assessment=_assessment(product, dimension, role, band, status=status),
        customer_priority=_priority(dimension) if priority else None,
    )


def test_product_only_turn_cannot_reuse_previously_active_customer_context() -> None:
    initial = PersonalizationBoundaryState(
        state_id="state:initial",
        state=PersonalizationState.PRODUCT_ONLY,
    )
    entered = decide_personalization_boundary(
        decision_id="boundary:enter",
        prior=initial,
        intent=TurnIntent.PERSONALIZED_DECISION_SUPPORT,
        customer_context_id="customer_context:mother",
    )
    assert entered.customer_context_access is CustomerContextAccess.PERMITTED

    exited = decide_personalization_boundary(
        decision_id="boundary:exit",
        prior=next_boundary_state(entered),
        intent=TurnIntent.PRODUCT_ONLY,
    )
    assert exited.customer_context_access is CustomerContextAccess.PROHIBITED
    assert exited.active_customer_context_id is None


def test_inferred_priority_cannot_drive_alignment_even_if_band_is_clear() -> None:
    assessment = _assessment(LEFT, "restoration", DecisionRole.CORE_PROTECTION, AssessmentBand.VERY_STRONG)
    with pytest.raises(DimensionAlignmentError, match="confirmed"):
        align_assessment_to_customer_priority(
            finding_id="finding:inferred-priority",
            product_reference=LEFT,
            assessment=assessment,
            customer_priority=_priority("restoration", CustomerContextProvenance.INFERRED),
        )


def test_inferred_circumstance_cannot_drive_governed_applicability() -> None:
    rule = CircumstanceRelevanceRule(
        rule_id="rule:entry-age-61",
        rule_version="1.0",
        circumstance_id="insured_entry_age_years",
        operator=CircumstanceOperator.GREATER_THAN_OR_EQUAL,
        expected_value=61,
        target_dimension_id="copayment",
        claim_type=RelevanceClaimType.PRODUCT_APPLICABILITY,
        effect=RelevanceEffect.CONDITION_POTENTIALLY_APPLICABLE,
        basis=RelevanceRuleBasis.PRODUCT_POLICY_MECHANIC,
        rationale="Governed conditional copayment age trigger.",
        evidence_reference_ids=("evidence:copayment-age-trigger",),
        review_status=ReviewStatus.APPROVED,
        publication_status=PublicationStatus.PUBLISHED,
        effective_from=date(2026, 1, 1),
    )
    fact = CustomerCircumstanceFact(
        fact_id="fact:entry-age",
        subject_reference="customer_subject:mother",
        circumstance_id="insured_entry_age_years",
        value=67,
        provenance=CustomerFactProvenance.INFERRED,
        raw_statement="She seems to have entered at age 67.",
    )
    with pytest.raises(CircumstanceRelevanceError, match="confirmed"):
        evaluate_circumstance_relevance(fact=fact, rule=rule, as_of=date(2026, 8, 9))


def test_protection_floor_survives_without_customer_priority_through_projection() -> None:
    left_copay = _alignment(
        LEFT,
        "copayment",
        DecisionRole.PROTECTION_FLOOR,
        AssessmentBand.RESTRICTIVE,
        priority=False,
    )
    right_copay = _alignment(
        RIGHT,
        "copayment",
        DecisionRole.PROTECTION_FLOOR,
        AssessmentBand.STRONG,
        priority=False,
    )
    left = ProductDecisionEvidence(product_reference=LEFT, alignments=(left_copay,))
    right = ProductDecisionEvidence(product_reference=RIGHT, alignments=(right_copay,))
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:floors",
        left=left,
        right=right,
    )
    projection = project_decision_support(
        projection_id="projection:floors",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )
    assert projection.left.protection_floor_findings == (left_copay,)
    assert projection.right.protection_floor_findings == (right_copay,)
    assert left_copay.status is DimensionAlignmentStatus.PROTECTION_FLOOR_UNPRIORITIZED


def test_product_unknown_blocks_projection_from_appearing_ready() -> None:
    left_unknown = _alignment(
        LEFT,
        "room_rent_restriction",
        DecisionRole.PROTECTION_FLOOR,
        None,
        status=AssessmentStatus.NOT_SCORABLE,
    )
    right_known = _alignment(
        RIGHT,
        "room_rent_restriction",
        DecisionRole.PROTECTION_FLOOR,
        AssessmentBand.STRONG,
    )
    left = ProductDecisionEvidence(product_reference=LEFT, alignments=(left_unknown,))
    right = ProductDecisionEvidence(product_reference=RIGHT, alignments=(right_known,))
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:unknown",
        left=left,
        right=right,
    )
    assert sufficiency.status is DecisionSufficiencyStatus.BLOCKED_BY_PRODUCT_UNKNOWN
    projection = project_decision_support(
        projection_id="projection:unknown",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )
    assert projection.left.unresolved_findings == (left_unknown,)
    assert projection.status.value == "ACTION_REQUIRED"


def test_both_products_failing_hard_constraints_never_crowns_less_bad_option() -> None:
    left = ProductDecisionEvidence(
        product_reference=LEFT,
        alignments=(_alignment(LEFT, "quoted_premium", DecisionRole.PRICE, AssessmentBand.MODERATE),),
        constraint_status=ProductConstraintStatus.FAILS_ONE_OR_MORE,
        failed_constraint_ids=("constraint:max-premium",),
    )
    right = ProductDecisionEvidence(
        product_reference=RIGHT,
        alignments=(_alignment(RIGHT, "quoted_premium", DecisionRole.PRICE, AssessmentBand.STRONG),),
        constraint_status=ProductConstraintStatus.FAILS_ONE_OR_MORE,
        failed_constraint_ids=("constraint:max-premium",),
    )
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:hard-constraints",
        left=left,
        right=right,
    )
    assert sufficiency.status is DecisionSufficiencyStatus.NEITHER_MEETS_HARD_CONSTRAINTS
    projection = project_decision_support(
        projection_id="projection:hard-constraints",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )
    assert projection.status.value == "ACTION_REQUIRED"


def test_set_inadequacy_blocks_any_global_market_implication() -> None:
    left = ProductDecisionEvidence(
        product_reference=LEFT,
        alignments=(_alignment(LEFT, "copayment", DecisionRole.PROTECTION_FLOOR, AssessmentBand.RESTRICTIVE),),
    )
    right = ProductDecisionEvidence(
        product_reference=RIGHT,
        alignments=(_alignment(RIGHT, "copayment", DecisionRole.PROTECTION_FLOOR, AssessmentBand.RESTRICTIVE),),
    )
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:set-inadequate",
        left=left,
        right=right,
        set_adequacy_signals=(SetAdequacySignal.SHARED_MATERIAL_WEAKNESS,),
    )
    assert sufficiency.status is DecisionSufficiencyStatus.SET_MAY_BE_INADEQUATE
    projection = project_decision_support(
        projection_id="projection:set-inadequate",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )
    assert "among the compared products" in projection.set_scope_statement.lower()
    assert "every product available in the market" in projection.set_scope_statement.lower()


def test_default_projection_contract_cannot_expose_verdict_fields_or_verdict_boundary() -> None:
    left = ProductDecisionEvidence(
        product_reference=LEFT,
        alignments=(_alignment(LEFT, "restoration", DecisionRole.CORE_PROTECTION, AssessmentBand.STRONG),),
    )
    right = ProductDecisionEvidence(
        product_reference=RIGHT,
        alignments=(_alignment(RIGHT, "restoration", DecisionRole.CORE_PROTECTION, AssessmentBand.VERY_STRONG),),
    )
    sufficiency = evaluate_decision_sufficiency(
        decision_id="sufficiency:no-verdict",
        left=left,
        right=right,
    )
    projection = project_decision_support(
        projection_id="projection:no-verdict",
        sufficiency=sufficiency,
        left=left,
        right=right,
    )
    forbidden_fields = {
        "score",
        "weight",
        "rank",
        "winner",
        "preferred_product",
        "recommended_product",
        "recommendation",
        "suitability",
        "lean",
        "net_direction",
    }
    assert forbidden_fields.isdisjoint(projection.__dataclass_fields__)
    lower = projection.decision_boundary.lower()
    assert "does not choose" in lower
    assert "user decides" in lower

    # Constructor-level guard also rejects a hand-crafted soft verdict boundary.
    from insurance_intelligence.decision_support.decision_projection import (
        GovernedDecisionSupportProjection,
    )
    with pytest.raises(DecisionProjectionError, match="verdict language"):
        GovernedDecisionSupportProjection(
            projection_id=projection.projection_id,
            sufficiency_decision_id=projection.sufficiency_decision_id,
            status=projection.status,
            left=projection.left,
            right=projection.right,
            set_scope_statement=projection.set_scope_statement,
            decision_boundary="Among the compared products, the evidence leans toward Product B; the user decides.",
            limitations=projection.limitations,
            blocking_reference_ids=projection.blocking_reference_ids,
        )
