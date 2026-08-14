from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.generic_knowledge.comparison_projection import (
    ComparableDimension,
    ComparisonProjectionError,
    NotApplicableDimension,
    NotApplicableReasonCode,
    NotComparableDimension,
    NotComparableReasonCode,
    ProjectionDisposition,
    classify_producer_state,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey


def _app() -> ApplicabilityKey:
    return ApplicabilityKey(product_reference="product:test")


def test_comparable_is_the_only_projection_variant_that_carries_value() -> None:
    comparable = ComparableDimension(
        concept_id="health:benefit:cataract",
        dimension_id="benefit_limit",
        source_family="benefit_limit",
        applicability=_app(),
        evidence_ids=("ev-1",),
        structured_value={"limit_kind": "PERCENTAGE", "percentage": 25.0},
    )
    blocked = NotComparableDimension(
        concept_id="health:benefit:cataract",
        dimension_id="benefit_limit",
        source_family="benefit_limit",
        applicability=_app(),
        evidence_ids=("ev-1",),
        reason_code=NotComparableReasonCode.COMPARISON_READINESS_BLOCKED,
        blocking_reasons=("cost-sharing ordering is unknown",),
        producer_state="INTERACTION_ORDERING_UNKNOWN",
    )
    not_applicable = NotApplicableDimension(
        concept_id="health:benefit:cataract",
        dimension_id="benefit_limit",
        source_family="benefit_limit",
        applicability=_app(),
        evidence_ids=("ev-2",),
        reason_code=NotApplicableReasonCode.EXPLICITLY_NON_APPLICABLE,
        reason="governed evidence establishes that this benefit does not apply",
    )

    assert comparable.disposition is ProjectionDisposition.COMPARABLE
    assert comparable.structured_value["percentage"] == 25.0
    assert blocked.disposition is ProjectionDisposition.NOT_COMPARABLE
    assert not_applicable.disposition is ProjectionDisposition.NOT_APPLICABLE
    assert not hasattr(blocked, "structured_value")
    assert not hasattr(not_applicable, "structured_value")


def test_structured_value_is_immutable_after_projection() -> None:
    comparable = ComparableDimension(
        concept_id="health:benefit:cataract",
        dimension_id="benefit_limit",
        source_family="benefit_limit",
        applicability=_app(),
        evidence_ids=("ev-1",),
        structured_value={"limit_kind": "PERCENTAGE"},
    )
    with pytest.raises(TypeError):
        comparable.structured_value["limit_kind"] = "NO_LIMIT"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        comparable.dimension_id = "other"  # type: ignore[misc]


def test_unknown_or_future_producer_state_fails_closed() -> None:
    disposition = classify_producer_state(
        "FUTURE_MOTOR_IDV_DEPRECIATION_BOUND",
        comparable_states=frozenset({"RESOLVED"}),
        not_applicable_states=frozenset({"EXPLICITLY_NON_APPLICABLE"}),
    )
    assert disposition is ProjectionDisposition.NOT_COMPARABLE


def test_state_correspondence_requires_explicit_positive_and_non_applicable_sets() -> None:
    assert (
        classify_producer_state(
            "RESOLVED",
            comparable_states=frozenset({"RESOLVED"}),
            not_applicable_states=frozenset({"EXPLICITLY_NON_APPLICABLE"}),
        )
        is ProjectionDisposition.COMPARABLE
    )
    assert (
        classify_producer_state(
            "EXPLICITLY_NON_APPLICABLE",
            comparable_states=frozenset({"RESOLVED"}),
            not_applicable_states=frozenset({"EXPLICITLY_NON_APPLICABLE"}),
        )
        is ProjectionDisposition.NOT_APPLICABLE
    )
    assert (
        classify_producer_state(
            "POLICY_SCHEDULE_BOUND",
            comparable_states=frozenset({"RESOLVED"}),
            not_applicable_states=frozenset({"EXPLICITLY_NON_APPLICABLE"}),
        )
        is ProjectionDisposition.NOT_COMPARABLE
    )


def test_contradictory_state_correspondence_is_rejected() -> None:
    with pytest.raises(ComparisonProjectionError):
        classify_producer_state(
            "RESOLVED",
            comparable_states=frozenset({"RESOLVED"}),
            not_applicable_states=frozenset({"RESOLVED"}),
        )


def test_not_comparable_requires_a_typed_reason_and_explanation() -> None:
    with pytest.raises(ComparisonProjectionError):
        NotComparableDimension(
            concept_id="health:benefit:cataract",
            dimension_id="benefit_limit",
            source_family="benefit_limit",
            applicability=_app(),
            evidence_ids=("ev-1",),
            reason_code=NotComparableReasonCode.RESOLUTION_BLOCKED,
            blocking_reasons=(),
            producer_state="POLICY_SCHEDULE_BOUND",
        )


def test_not_applicable_is_not_constructible_without_governed_evidence() -> None:
    with pytest.raises(ComparisonProjectionError):
        NotApplicableDimension(
            concept_id="health:benefit:cataract",
            dimension_id="benefit_limit",
            source_family="benefit_limit",
            applicability=_app(),
            evidence_ids=(),
            reason_code=NotApplicableReasonCode.EXPLICITLY_NON_APPLICABLE,
            reason="does not apply",
        )


def test_projection_preserves_applicability_and_evidence_identity() -> None:
    applicability = ApplicabilityKey(
        product_reference="product:test",
        policy_version="2026",
        variant="gold",
    )
    projected = NotComparableDimension(
        concept_id="health:benefit:cataract",
        dimension_id="benefit_limit",
        source_family="benefit_limit",
        applicability=applicability,
        evidence_ids=("ev-1", "ev-2"),
        reason_code=NotComparableReasonCode.RESOLUTION_BLOCKED,
        blocking_reasons=("policy schedule is required",),
        producer_state="POLICY_SCHEDULE_BOUND",
    )
    assert projected.applicability == applicability
    assert projected.evidence_ids == ("ev-1", "ev-2")
