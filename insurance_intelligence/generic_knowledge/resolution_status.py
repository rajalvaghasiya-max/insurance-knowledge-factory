"""Computed resolution-state contracts for MO-028B.G11.C1.

Accounting answers whether a normative unit received an explicit disposition. Resolution answers
whether governed semantic knowledge can currently produce a valid insurance answer. These are
orthogonal concerns.

Resolution status is deliberately derived from validated state inputs. Callers do not author a
status directly. Product or instance identity may appear as data elsewhere, but this module must
never branch on insurer or product identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Iterable

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError


class ResolutionContractError(GenericKnowledgeContractError):
    """Raised when generic resolution-state inputs violate invariants."""


class ResolutionSeverity(IntEnum):
    """Ordering used only to choose the most blocking resolution class."""

    RESOLVED = 0
    INSTANCE_BOUND = 10
    GOVERNANCE_BLOCKED = 20
    REPRESENTATIONALLY_BLOCKED = 30
    VALIDATION_BLOCKED = 40


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"

    POLICY_SCHEDULE_BOUND = "POLICY_SCHEDULE_BOUND"
    INSTANCE_CONDITION_REQUIRED = "INSTANCE_CONDITION_REQUIRED"
    OPERAND_INSTANCE_BOUND = "OPERAND_INSTANCE_BOUND"

    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    SOURCE_STALE = "SOURCE_STALE"
    REGULATORY_VERIFICATION_REQUIRED = "REGULATORY_VERIFICATION_REQUIRED"
    OPERAND_GOVERNANCE_BLOCKED = "OPERAND_GOVERNANCE_BLOCKED"

    NOT_YET_REPRESENTABLE = "NOT_YET_REPRESENTABLE"
    SEMANTIC_CONFLICT = "SEMANTIC_CONFLICT"
    OPERAND_REPRESENTATIONALLY_BLOCKED = "OPERAND_REPRESENTATIONALLY_BLOCKED"

    VALIDATION_CONFLICT = "VALIDATION_CONFLICT"


_STATUS_SEVERITY = {
    ResolutionStatus.RESOLVED: ResolutionSeverity.RESOLVED,
    ResolutionStatus.POLICY_SCHEDULE_BOUND: ResolutionSeverity.INSTANCE_BOUND,
    ResolutionStatus.INSTANCE_CONDITION_REQUIRED: ResolutionSeverity.INSTANCE_BOUND,
    ResolutionStatus.OPERAND_INSTANCE_BOUND: ResolutionSeverity.INSTANCE_BOUND,
    ResolutionStatus.REVIEW_REQUIRED: ResolutionSeverity.GOVERNANCE_BLOCKED,
    ResolutionStatus.SOURCE_STALE: ResolutionSeverity.GOVERNANCE_BLOCKED,
    ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED: ResolutionSeverity.GOVERNANCE_BLOCKED,
    ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED: ResolutionSeverity.GOVERNANCE_BLOCKED,
    ResolutionStatus.NOT_YET_REPRESENTABLE: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
    ResolutionStatus.SEMANTIC_CONFLICT: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
    ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED: ResolutionSeverity.REPRESENTATIONALLY_BLOCKED,
    ResolutionStatus.VALIDATION_CONFLICT: ResolutionSeverity.VALIDATION_BLOCKED,
}


class ValueSource(str, Enum):
    """Where the effective semantic value is expected to come from."""

    PRODUCT_RESOLVED = "PRODUCT_RESOLVED"
    POLICY_SCHEDULE_SELECTED = "POLICY_SCHEDULE_SELECTED"
    POLICY_INSTANCE_CONDITION = "POLICY_INSTANCE_CONDITION"


class InstanceAvailability(str, Enum):
    NOT_REQUIRED = "NOT_REQUIRED"
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"


class RepresentationState(str, Enum):
    REPRESENTABLE = "REPRESENTABLE"
    NOT_YET_REPRESENTABLE = "NOT_YET_REPRESENTABLE"
    SEMANTIC_CONFLICT = "SEMANTIC_CONFLICT"


class ReviewState(str, Enum):
    APPROVED = "APPROVED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REGULATORY_VERIFICATION_REQUIRED = "REGULATORY_VERIFICATION_REQUIRED"


class SourceState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"


class ValidationState(str, Enum):
    VALID = "VALID"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class ResolutionInputs:
    """Validated state from which resolution status is computed.

    There is intentionally no ``resolution_status`` field. A caller cannot author a status that
    disagrees with the value source, instance availability, representation, review, source, or
    validation state.
    """

    value_source: ValueSource
    instance_availability: InstanceAvailability = InstanceAvailability.NOT_REQUIRED
    representation_state: RepresentationState = RepresentationState.REPRESENTABLE
    review_state: ReviewState = ReviewState.APPROVED
    source_state: SourceState = SourceState.CURRENT
    validation_state: ValidationState = ValidationState.VALID

    def __post_init__(self) -> None:
        for field_name, enum_type in (
            ("value_source", ValueSource),
            ("instance_availability", InstanceAvailability),
            ("representation_state", RepresentationState),
            ("review_state", ReviewState),
            ("source_state", SourceState),
            ("validation_state", ValidationState),
        ):
            if not isinstance(getattr(self, field_name), enum_type):
                raise ResolutionContractError(f"{field_name} must be {enum_type.__name__}")

        if (
            self.value_source is ValueSource.PRODUCT_RESOLVED
            and self.instance_availability is not InstanceAvailability.NOT_REQUIRED
        ):
            raise ResolutionContractError(
                "PRODUCT_RESOLVED values must use NOT_REQUIRED instance availability"
            )
        if (
            self.value_source is not ValueSource.PRODUCT_RESOLVED
            and self.instance_availability is InstanceAvailability.NOT_REQUIRED
        ):
            raise ResolutionContractError(
                "instance-bound value sources must declare AVAILABLE or MISSING instance state"
            )


@dataclass(frozen=True)
class ComputedResolution:
    status: ResolutionStatus
    severity: ResolutionSeverity
    causes: tuple[ResolutionStatus, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ResolutionStatus):
            raise ResolutionContractError("status must be ResolutionStatus")
        if not isinstance(self.severity, ResolutionSeverity):
            raise ResolutionContractError("severity must be ResolutionSeverity")
        if self.severity is not resolution_severity(self.status):
            raise ResolutionContractError("severity must match the computed status")
        if any(not isinstance(cause, ResolutionStatus) for cause in self.causes):
            raise ResolutionContractError("causes must contain ResolutionStatus values")


def resolution_severity(status: ResolutionStatus) -> ResolutionSeverity:
    if not isinstance(status, ResolutionStatus):
        raise ResolutionContractError("status must be ResolutionStatus")
    return _STATUS_SEVERITY[status]


def _computed(status: ResolutionStatus, *causes: ResolutionStatus) -> ComputedResolution:
    return ComputedResolution(
        status=status,
        severity=resolution_severity(status),
        causes=tuple(causes),
    )


def compute_resolution_status(inputs: ResolutionInputs) -> ComputedResolution:
    """Derive the only valid resolution status for one semantic value cell.

    Ordering is deliberately fail-closed:
      deterministic validation contradiction
      > representational/semantic block
      > governance/source block
      > missing policy instance
      > resolved.
    """
    if not isinstance(inputs, ResolutionInputs):
        raise ResolutionContractError("inputs must be ResolutionInputs")

    if inputs.validation_state is ValidationState.CONFLICT:
        return _computed(ResolutionStatus.VALIDATION_CONFLICT)

    if inputs.representation_state is RepresentationState.SEMANTIC_CONFLICT:
        return _computed(ResolutionStatus.SEMANTIC_CONFLICT)
    if inputs.representation_state is RepresentationState.NOT_YET_REPRESENTABLE:
        return _computed(ResolutionStatus.NOT_YET_REPRESENTABLE)

    if inputs.source_state is SourceState.STALE:
        return _computed(ResolutionStatus.SOURCE_STALE)
    if inputs.review_state is ReviewState.REVIEW_REQUIRED:
        return _computed(ResolutionStatus.REVIEW_REQUIRED)
    if inputs.review_state is ReviewState.REGULATORY_VERIFICATION_REQUIRED:
        return _computed(ResolutionStatus.REGULATORY_VERIFICATION_REQUIRED)

    if inputs.instance_availability is InstanceAvailability.MISSING:
        if inputs.value_source is ValueSource.POLICY_SCHEDULE_SELECTED:
            return _computed(ResolutionStatus.POLICY_SCHEDULE_BOUND)
        if inputs.value_source is ValueSource.POLICY_INSTANCE_CONDITION:
            return _computed(ResolutionStatus.INSTANCE_CONDITION_REQUIRED)

    return _computed(ResolutionStatus.RESOLVED)


def most_blocking_status(statuses: Iterable[ResolutionStatus]) -> ComputedResolution:
    """Return the most-blocking status while retaining the contributing causes.

    C1 provides the lattice primitive only. C2 will define relationship-specific propagation
    such as LONGER_OF and DERIVES_FROM using this primitive.
    """
    normalized = tuple(statuses)
    if not normalized:
        raise ResolutionContractError("statuses must not be empty")
    if any(not isinstance(status, ResolutionStatus) for status in normalized):
        raise ResolutionContractError("statuses must contain ResolutionStatus values")
    status = max(normalized, key=resolution_severity)
    return _computed(status, *normalized)


__all__ = [
    "ComputedResolution",
    "InstanceAvailability",
    "RepresentationState",
    "ResolutionContractError",
    "ResolutionInputs",
    "ResolutionSeverity",
    "ResolutionStatus",
    "ReviewState",
    "SourceState",
    "ValidationState",
    "ValueSource",
    "compute_resolution_status",
    "most_blocking_status",
    "resolution_severity",
]
