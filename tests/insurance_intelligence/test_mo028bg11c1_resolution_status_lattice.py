from __future__ import annotations

import pytest

from insurance_intelligence.generic_knowledge.resolution_status import (
    InstanceAvailability,
    RepresentationState,
    ResolutionContractError,
    ResolutionInputs,
    ResolutionSeverity,
    ResolutionStatus,
    ReviewState,
    SourceState,
    ValidationState,
    ValueSource,
    compute_resolution_status,
    most_blocking_status,
    resolution_severity,
)


def test_product_resolved_value_is_resolved_without_instance() -> None:
    result = compute_resolution_status(
        ResolutionInputs(value_source=ValueSource.PRODUCT_RESOLVED)
    )
    assert result.status is ResolutionStatus.RESOLVED
    assert result.severity is ResolutionSeverity.RESOLVED


def test_schedule_selected_value_without_instance_is_policy_schedule_bound() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assert result.status is ResolutionStatus.POLICY_SCHEDULE_BOUND
    assert result.severity is ResolutionSeverity.INSTANCE_BOUND


def test_schedule_selected_value_with_instance_can_be_resolved() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.AVAILABLE,
        )
    )
    assert result.status is ResolutionStatus.RESOLVED


def test_policy_instance_condition_without_instance_is_distinct_from_schedule_bound() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_INSTANCE_CONDITION,
            instance_availability=InstanceAvailability.MISSING,
        )
    )
    assert result.status is ResolutionStatus.INSTANCE_CONDITION_REQUIRED
    assert result.status is not ResolutionStatus.POLICY_SCHEDULE_BOUND


def test_not_yet_representable_outranks_missing_instance() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
            representation_state=RepresentationState.NOT_YET_REPRESENTABLE,
        )
    )
    assert result.status is ResolutionStatus.NOT_YET_REPRESENTABLE
    assert result.severity is ResolutionSeverity.REPRESENTATIONALLY_BLOCKED


def test_semantic_conflict_is_distinct_from_validation_conflict() -> None:
    semantic = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            representation_state=RepresentationState.SEMANTIC_CONFLICT,
        )
    )
    validation = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            validation_state=ValidationState.CONFLICT,
        )
    )
    assert semantic.status is ResolutionStatus.SEMANTIC_CONFLICT
    assert validation.status is ResolutionStatus.VALIDATION_CONFLICT
    assert semantic.status is not validation.status


def test_validation_conflict_is_most_blocking_computed_state() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
            representation_state=RepresentationState.NOT_YET_REPRESENTABLE,
            review_state=ReviewState.REVIEW_REQUIRED,
            source_state=SourceState.STALE,
            validation_state=ValidationState.CONFLICT,
        )
    )
    assert result.status is ResolutionStatus.VALIDATION_CONFLICT
    assert result.severity is ResolutionSeverity.VALIDATION_BLOCKED


def test_governance_block_outranks_instance_bound() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.POLICY_SCHEDULE_SELECTED,
            instance_availability=InstanceAvailability.MISSING,
            review_state=ReviewState.REVIEW_REQUIRED,
        )
    )
    assert result.status is ResolutionStatus.REVIEW_REQUIRED
    assert result.severity is ResolutionSeverity.GOVERNANCE_BLOCKED


def test_source_stale_is_explicit_governance_block() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            source_state=SourceState.STALE,
        )
    )
    assert result.status is ResolutionStatus.SOURCE_STALE


def test_regulatory_verification_required_is_not_absence_or_representation_failure() -> None:
    result = compute_resolution_status(
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            review_state=ReviewState.REGULATORY_VERIFICATION_REQUIRED,
        )
    )
    assert result.status is ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED
    assert result.severity is ResolutionSeverity.GOVERNANCE_BLOCKED


def test_resolution_status_cannot_be_authored_on_inputs() -> None:
    assert "resolution_status" not in ResolutionInputs.__dataclass_fields__
    assert "status" not in ResolutionInputs.__dataclass_fields__


def test_product_resolved_rejects_instance_availability() -> None:
    with pytest.raises(ResolutionContractError):
        ResolutionInputs(
            value_source=ValueSource.PRODUCT_RESOLVED,
            instance_availability=InstanceAvailability.AVAILABLE,
        )


def test_instance_bound_source_requires_explicit_instance_state() -> None:
    with pytest.raises(ResolutionContractError):
        ResolutionInputs(value_source=ValueSource.POLICY_SCHEDULE_SELECTED)


def test_lattice_preserves_specific_status_causes() -> None:
    result = most_blocking_status(
        (
            ResolutionStatus.RESOLVED,
            ResolutionStatus.POLICY_SCHEDULE_BOUND,
            ResolutionStatus.NOT_YET_REPRESENTABLE,
        )
    )
    assert result.status is ResolutionStatus.NOT_YET_REPRESENTABLE
    assert result.causes == (
        ResolutionStatus.RESOLVED,
        ResolutionStatus.POLICY_SCHEDULE_BOUND,
        ResolutionStatus.NOT_YET_REPRESENTABLE,
    )


def test_lattice_distinguishes_instance_and_representation_blocks() -> None:
    assert resolution_severity(ResolutionStatus.POLICY_SCHEDULE_BOUND) is ResolutionSeverity.INSTANCE_BOUND
    assert (
        resolution_severity(ResolutionStatus.NOT_YET_REPRESENTABLE)
        is ResolutionSeverity.REPRESENTATIONALLY_BLOCKED
    )
    assert (
        resolution_severity(ResolutionStatus.NOT_YET_REPRESENTABLE)
        > resolution_severity(ResolutionStatus.POLICY_SCHEDULE_BOUND)
    )


def test_c1_does_not_pretend_to_define_relationship_specific_propagation() -> None:
    # C1 owns the lattice only. C2 will translate operand classes to explicit
    # OPERAND_* statuses for LONGER_OF / DERIVES_FROM semantics.
    result = most_blocking_status(
        (ResolutionStatus.POLICY_SCHEDULE_BOUND, ResolutionStatus.RESOLVED)
    )
    assert result.status is ResolutionStatus.POLICY_SCHEDULE_BOUND
    assert ResolutionStatus.OPERAND_INSTANCE_BOUND in ResolutionStatus
