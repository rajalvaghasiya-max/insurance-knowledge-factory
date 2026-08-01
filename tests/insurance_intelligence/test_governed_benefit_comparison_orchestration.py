from dataclasses import replace
from datetime import date, timedelta

import pytest

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.benefits.eligibility import ComparisonEligibilityStatus
from insurance_intelligence.benefits.orchestration import (
    ComparisonOrchestrationError,
    ComparisonOrchestrationStatus,
    GovernedComparisonOutcome,
    GovernedComparisonRequest,
    orchestrate_governed_comparison,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)


AS_OF = date(2026, 8, 1)
LEFT_ID = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION.implementation_id
RIGHT_ID = ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION.implementation_id
REGISTRY = (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
    ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
)


def _request(**overrides):
    values = {
        "concept_id": RESTORATION_CONCEPT_ID,
        "left_implementation_id": LEFT_ID,
        "right_implementation_id": RIGHT_ID,
        "as_of": AS_OF,
    }
    values.update(overrides)
    return GovernedComparisonRequest(**values)


def test_request_normalizes_text():
    request = GovernedComparisonRequest(
        concept_id=f" {RESTORATION_CONCEPT_ID} ",
        left_implementation_id=f" {LEFT_ID} ",
        right_implementation_id=f" {RIGHT_ID} ",
        as_of=AS_OF,
    )
    assert request.concept_id == RESTORATION_CONCEPT_ID
    assert request.left_implementation_id == LEFT_ID
    assert request.right_implementation_id == RIGHT_ID


@pytest.mark.parametrize(
    "field_name",
    ("concept_id", "left_implementation_id", "right_implementation_id"),
)
def test_request_rejects_empty_text(field_name):
    with pytest.raises(ComparisonOrchestrationError):
        _request(**{field_name: " "})


def test_request_rejects_same_identity():
    with pytest.raises(ComparisonOrchestrationError):
        _request(right_implementation_id=LEFT_ID)


def test_request_rejects_non_date():
    with pytest.raises(ComparisonOrchestrationError):
        _request(as_of="2026-08-01")


def test_orchestration_rejects_wrong_request_type():
    with pytest.raises(ComparisonOrchestrationError):
        orchestrate_governed_comparison("not-a-request", registry=REGISTRY)


def test_real_pair_completes_with_partial_source_eligibility():
    result = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    assert result.status is ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY
    assert result.eligibility is not None
    assert result.eligibility.status is ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
    assert result.comparison is not None
    assert not result.comparison.blocked_dimensions
    assert result.discovered_implementation_ids == tuple(sorted((LEFT_ID, RIGHT_ID)))


def test_real_pair_preserves_requested_orientation():
    result = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    assert result.comparison.left.implementation_id == LEFT_ID
    assert result.comparison.right.implementation_id == RIGHT_ID


def test_real_pair_exposes_factual_frequency_difference():
    result = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    dimensions = {item.dimension_id: item for item in result.comparison.dimensions}
    frequency = dimensions["restoration_frequency_type"]
    assert frequency.left_value == "FINITE"
    assert frequency.right_value == "UNLIMITED"


def test_real_pair_exposes_same_hospitalization_difference():
    result = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    dimensions = {item.dimension_id: item for item in result.comparison.dimensions}
    mechanic = dimensions["same_hospitalization_use"]
    assert mechanic.left_value is False
    assert mechanic.right_value is True


def test_result_contains_governance_limitations():
    result = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    joined = " ".join(result.limitations).lower()
    assert "not a ranking" in joined
    assert "claim assessment" in joined
    assert "partial eligibility" in joined


def test_unknown_left_identity_is_blocked():
    result = orchestrate_governed_comparison(
        _request(left_implementation_id="benefit_impl:missing:left"), registry=REGISTRY
    )
    assert result.status is ComparisonOrchestrationStatus.BLOCKED
    assert result.eligibility is None
    assert result.comparison is None
    assert "left implementation" in result.reasons[0]


def test_unknown_right_identity_is_blocked():
    result = orchestrate_governed_comparison(
        _request(right_implementation_id="benefit_impl:missing:right"), registry=REGISTRY
    )
    assert result.status is ComparisonOrchestrationStatus.BLOCKED
    assert result.eligibility is None
    assert result.comparison is None
    assert "right implementation" in result.reasons[0]


def test_wrong_concept_is_blocked_by_discovery():
    result = orchestrate_governed_comparison(
        _request(concept_id="benefit_concept:health:unknown"), registry=REGISTRY
    )
    assert result.is_blocked
    assert result.discovered_implementation_ids == ()
    assert len(result.reasons) == 2


def test_unpublished_requested_implementation_is_not_discovered():
    unpublished = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        publication_status=PublicationStatus.DRAFT,
    )
    result = orchestrate_governed_comparison(
        _request(), registry=(unpublished, ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    )
    assert result.is_blocked
    assert LEFT_ID not in result.discovered_implementation_ids


def test_unapproved_requested_implementation_is_not_discovered():
    unapproved = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        review_status=ReviewStatus.PENDING,
    )
    result = orchestrate_governed_comparison(
        _request(), registry=(unapproved, ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    )
    assert result.is_blocked
    assert LEFT_ID not in result.discovered_implementation_ids


def test_not_yet_effective_implementation_is_not_discovered():
    future = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        effective_from=AS_OF + timedelta(days=1),
    )
    result = orchestrate_governed_comparison(
        _request(), registry=(future, ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    )
    assert result.is_blocked
    assert LEFT_ID not in result.discovered_implementation_ids


def test_expired_implementation_is_not_discovered():
    expired = replace(
        STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
        effective_to=AS_OF - timedelta(days=1),
    )
    result = orchestrate_governed_comparison(
        _request(), registry=(expired, ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION)
    )
    assert result.is_blocked
    assert LEFT_ID not in result.discovered_implementation_ids


def test_duplicate_discovered_identity_is_rejected():
    with pytest.raises(ComparisonOrchestrationError, match="duplicate discovered"):
        orchestrate_governed_comparison(
            _request(),
            registry=(
                STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
                STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
                ACTIV_ONE_NXT_RESTORATION_IMPLEMENTATION,
            ),
        )


def test_outcome_requires_comparison_when_not_blocked():
    with pytest.raises(ComparisonOrchestrationError):
        GovernedComparisonOutcome(
            status=ComparisonOrchestrationStatus.COMPLETED,
            request=_request(),
            discovered_implementation_ids=tuple(sorted((LEFT_ID, RIGHT_ID))),
            eligibility=None,
            comparison=None,
            reasons=("reason",),
            limitations=("limitation",),
        )


def test_outcome_rejects_comparison_when_blocked():
    valid = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    with pytest.raises(ComparisonOrchestrationError):
        GovernedComparisonOutcome(
            status=ComparisonOrchestrationStatus.BLOCKED,
            request=_request(),
            discovered_implementation_ids=valid.discovered_implementation_ids,
            eligibility=valid.eligibility,
            comparison=valid.comparison,
            reasons=("reason",),
            limitations=("limitation",),
        )


def test_result_helpers_reflect_status():
    completed = orchestrate_governed_comparison(_request(), registry=REGISTRY)
    blocked = orchestrate_governed_comparison(
        _request(left_implementation_id="benefit_impl:missing:left"), registry=REGISTRY
    )
    assert completed.is_completed is False
    assert completed.is_blocked is False
    assert blocked.is_blocked is True
