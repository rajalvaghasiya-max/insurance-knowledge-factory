from __future__ import annotations

from datetime import date

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.comparison import ComparisonDimensionStatus
from insurance_intelligence.benefits.discovery import (
    BenefitDiscoveryRequest,
    discover_benefits,
)
from insurance_intelligence.benefits.eligibility import (
    ComparisonEligibilityRequest,
    ComparisonEligibilityStatus,
    evaluate_comparison_eligibility,
)
from insurance_intelligence.benefits.explanation_projection import (
    ExplanationProjectionStatus,
    project_comparison_explanation,
)
from insurance_intelligence.benefits.governed_handoff import (
    GovernedComparisonHandoff,
    build_governed_comparison_handoff,
)
from insurance_intelligence.benefits.normalization import normalize_for_comparison
from insurance_intelligence.benefits.orchestration import (
    ComparisonOrchestrationStatus,
    GovernedComparisonRequest,
    orchestrate_governed_comparison,
)
from insurance_intelligence.benefits.registry import registered_benefit_implementations
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)

AS_OF = date(2026, 8, 9)
LEFT = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION
RIGHT = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION


def test_mo025_discovery_returns_both_governed_restoration_implementations() -> None:
    result = discover_benefits(
        BenefitDiscoveryRequest(concept_id=RESTORATION_CONCEPT_ID, as_of=AS_OF)
    )

    assert result.count == 2
    assert tuple(item.implementation_id for item in result.implementations) == tuple(
        sorted((LEFT.implementation_id, RIGHT.implementation_id))
    )
    assert all(item.is_governed_for_use for item in result.implementations)


def test_mo025_source_record_eligibility_remains_partial_and_explicit() -> None:
    result = evaluate_comparison_eligibility(
        ComparisonEligibilityRequest(left=LEFT, right=RIGHT, as_of=AS_OF)
    )

    assert result.status is ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
    assert result.may_compare is True
    assert "restoration_percentage" in result.blocked_dimensions
    assert "restoration_count_per_policy_period" in result.blocked_dimensions


def test_mo025_normalization_preserves_identity_and_evidence() -> None:
    left = normalize_for_comparison(LEFT)
    right = normalize_for_comparison(RIGHT)

    assert left.implementation_id == LEFT.implementation_id
    assert right.implementation_id == RIGHT.implementation_id
    assert left.concept_id == right.concept_id == RESTORATION_CONCEPT_ID
    assert all(
        mechanic.evidence_reference_ids
        for projection in (left, right)
        for mechanic in projection.mechanics.values()
    )


def test_mo025_orchestration_completes_factual_comparison_without_blocked_dimensions() -> None:
    result = orchestrate_governed_comparison(
        GovernedComparisonRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            left_implementation_id=LEFT.implementation_id,
            right_implementation_id=RIGHT.implementation_id,
            as_of=AS_OF,
        )
    )

    assert result.status is ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY
    assert result.comparison is not None
    assert result.comparison.blocked_dimensions == ()

    dimensions = {item.dimension_id: item for item in result.comparison.dimensions}
    assert dimensions["restoration_amount_percentage_per_activation"].status is ComparisonDimensionStatus.SHARED
    assert dimensions["restoration_frequency_type"].status is ComparisonDimensionStatus.DIFFERENT
    assert dimensions["same_hospitalization_use"].status is ComparisonDimensionStatus.DIFFERENT


def test_mo025_projection_preserves_factual_differences_and_source_limitations() -> None:
    outcome = orchestrate_governed_comparison(
        GovernedComparisonRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            left_implementation_id=LEFT.implementation_id,
            right_implementation_id=RIGHT.implementation_id,
            as_of=AS_OF,
        )
    )
    projection = project_comparison_explanation(outcome)

    assert projection.status is ExplanationProjectionStatus.READY_WITH_SOURCE_LIMITATIONS
    assert projection.left.product_id == "star_comprehensive"
    assert projection.right.product_id == "activ_one"
    assert {item.dimension_id for item in projection.different_mechanics} >= {
        "restoration_frequency_type",
        "same_hospitalization_use",
    }


def test_mo025_only_governed_projection_crosses_pre_ranking_boundary() -> None:
    outcome = orchestrate_governed_comparison(
        GovernedComparisonRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            left_implementation_id=LEFT.implementation_id,
            right_implementation_id=RIGHT.implementation_id,
            as_of=AS_OF,
        )
    )
    projection = project_comparison_explanation(outcome)
    handoff = build_governed_comparison_handoff(projection)

    assert isinstance(handoff, GovernedComparisonHandoff)
    assert handoff.projection is projection
    assert handoff.concept_id == RESTORATION_CONCEPT_ID
    assert handoff.as_of == AS_OF


def test_mo025_boundary_contains_no_ranking_or_recommendation_output() -> None:
    registry = registered_benefit_implementations()
    outcome = orchestrate_governed_comparison(
        GovernedComparisonRequest(
            concept_id=RESTORATION_CONCEPT_ID,
            left_implementation_id=LEFT.implementation_id,
            right_implementation_id=RIGHT.implementation_id,
            as_of=AS_OF,
        ),
        registry=registry,
    )
    projection = project_comparison_explanation(outcome)
    handoff = build_governed_comparison_handoff(projection)

    for value in (outcome, projection, handoff):
        assert not hasattr(value, "winner")
        assert not hasattr(value, "ranking")
        assert not hasattr(value, "recommendation")
        assert not hasattr(value, "suitability")
