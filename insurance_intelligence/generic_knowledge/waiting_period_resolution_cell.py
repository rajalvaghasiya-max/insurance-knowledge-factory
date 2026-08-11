"""Waiting-period resolution-cell contracts for MO-028B.G11.C3.

C3 keeps independent insurance dimensions orthogonal:
- person event timing: when this person's exposure starts in the current policy context;
- continuity source: whether eligible prior waiting-period credit comes from portability/migration;
- amount portion: base coverage versus a dated enhancement tranche;
- value source: where the duration/effective value is resolved.

This remains waiting-period specific. It intentionally wraps the existing generic ApplicabilityKey
rather than widening that shared contract before cross-concept reuse is proven.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodScopeType,
    WaitingPeriodType,
)
from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.resolution_status import (
    ComputedResolution,
    InstanceAvailability,
    ResolutionInputs,
    ReviewState,
    ValueSource,
    compute_resolution_status,
)


class WaitingPeriodResolutionCellError(ValueError):
    """Raised when a waiting-period resolution cell violates an invariant."""


class PersonEventTiming(str, Enum):
    POLICY_INCEPTION = "POLICY_INCEPTION"
    MEMBER_ADDITION = "MEMBER_ADDITION"


class ContinuitySource(str, Enum):
    NONE = "NONE"
    PORTED = "PORTED"
    MIGRATED = "MIGRATED"
    UNRESOLVED = "UNRESOLVED"


class AmountPortionKind(str, Enum):
    BASE = "BASE"
    ENHANCEMENT_TRANCHE = "ENHANCEMENT_TRANCHE"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodResolutionCellError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class AmountPortionIdentity:
    kind: AmountPortionKind
    effective_from: date | None = None
    tranche_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, AmountPortionKind):
            raise WaitingPeriodResolutionCellError("kind must be AmountPortionKind")
        if self.effective_from is not None and not isinstance(self.effective_from, date):
            raise WaitingPeriodResolutionCellError("effective_from must be a date or None")
        if self.tranche_reference is not None:
            object.__setattr__(
                self,
                "tranche_reference",
                _text(self.tranche_reference, "tranche_reference"),
            )

        if self.kind is AmountPortionKind.BASE:
            if self.effective_from is not None or self.tranche_reference is not None:
                raise WaitingPeriodResolutionCellError(
                    "BASE amount portion must not define enhancement effective date or tranche reference"
                )
        else:
            if self.effective_from is None:
                raise WaitingPeriodResolutionCellError(
                    "ENHANCEMENT_TRANCHE requires effective_from reset anchor"
                )
            if self.tranche_reference is None:
                raise WaitingPeriodResolutionCellError(
                    "ENHANCEMENT_TRANCHE requires tranche_reference"
                )


@dataclass(frozen=True)
class WaitingPeriodResolutionCell:
    applicability: ApplicabilityKey
    waiting_period_type: WaitingPeriodType
    scope_type: WaitingPeriodScopeType
    person_event_timing: PersonEventTiming
    continuity_source: ContinuitySource
    amount_portion: AmountPortionIdentity
    value_source: ValueSource
    scope_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.applicability, ApplicabilityKey):
            raise WaitingPeriodResolutionCellError("applicability must be ApplicabilityKey")
        if not isinstance(self.waiting_period_type, WaitingPeriodType):
            raise WaitingPeriodResolutionCellError("waiting_period_type must be WaitingPeriodType")
        if not isinstance(self.scope_type, WaitingPeriodScopeType):
            raise WaitingPeriodResolutionCellError("scope_type must be WaitingPeriodScopeType")
        if not isinstance(self.person_event_timing, PersonEventTiming):
            raise WaitingPeriodResolutionCellError("person_event_timing must be PersonEventTiming")
        if not isinstance(self.continuity_source, ContinuitySource):
            raise WaitingPeriodResolutionCellError("continuity_source must be ContinuitySource")
        if not isinstance(self.amount_portion, AmountPortionIdentity):
            raise WaitingPeriodResolutionCellError("amount_portion must be AmountPortionIdentity")
        if not isinstance(self.value_source, ValueSource):
            raise WaitingPeriodResolutionCellError("value_source must be ValueSource")

        if self.scope_reference is not None:
            object.__setattr__(
                self,
                "scope_reference",
                _text(self.scope_reference, "scope_reference"),
            )
        if self.scope_type is WaitingPeriodScopeType.BENEFIT_SCOPED:
            if self.scope_reference is None:
                raise WaitingPeriodResolutionCellError(
                    "BENEFIT_SCOPED requires scope_reference"
                )
        elif self.scope_reference is not None:
            raise WaitingPeriodResolutionCellError(
                "POLICY_WIDE must not define scope_reference"
            )

    @property
    def dependency_identity(self) -> tuple[object, ...]:
        """Identity required for C2 operand joins; value source is deliberately excluded.

        Mixed value sources may share a cell, but the C2 resolver still requires both operands to
        reach RESOLVED before effective arithmetic may occur.
        """
        return (
            self.applicability,
            self.scope_type,
            self.scope_reference,
            self.person_event_timing,
            self.continuity_source,
            self.amount_portion,
        )


def continuity_resolution(cell: WaitingPeriodResolutionCell) -> ComputedResolution:
    """Return the C1 resolution state needed for exact continuity treatment.

    UNRESOLVED means classification/evidence is incomplete, not structurally impossible.
    MIGRATED remains representable while exact credit semantics await regulatory verification.
    """
    if not isinstance(cell, WaitingPeriodResolutionCell):
        raise WaitingPeriodResolutionCellError("cell must be WaitingPeriodResolutionCell")
    review_state = ReviewState.APPROVED
    if cell.continuity_source is ContinuitySource.UNRESOLVED:
        review_state = ReviewState.REVIEW_REQUIRED
    elif cell.continuity_source is ContinuitySource.MIGRATED:
        review_state = ReviewState.REGULATORY_VERIFICATION_REQUIRED

    instance_state = (
        InstanceAvailability.NOT_REQUIRED
        if cell.value_source is ValueSource.PRODUCT_RESOLVED
        else InstanceAvailability.MISSING
    )
    return compute_resolution_status(
        ResolutionInputs(
            value_source=cell.value_source,
            instance_availability=instance_state,
            review_state=review_state,
        )
    )


def conservative_continuity_source(cell: WaitingPeriodResolutionCell) -> ContinuitySource:
    """Return a safe interim continuity assumption without mutating the governed classification."""
    if not isinstance(cell, WaitingPeriodResolutionCell):
        raise WaitingPeriodResolutionCellError("cell must be WaitingPeriodResolutionCell")
    if cell.continuity_source is ContinuitySource.UNRESOLVED:
        return ContinuitySource.NONE
    return cell.continuity_source


def cells_compatible_for_dependency_join(
    left: WaitingPeriodResolutionCell,
    right: WaitingPeriodResolutionCell,
) -> bool:
    if not isinstance(left, WaitingPeriodResolutionCell) or not isinstance(
        right, WaitingPeriodResolutionCell
    ):
        raise WaitingPeriodResolutionCellError(
            "left and right must be WaitingPeriodResolutionCell values"
        )
    return left.dependency_identity == right.dependency_identity


__all__ = [
    "AmountPortionIdentity",
    "AmountPortionKind",
    "ContinuitySource",
    "PersonEventTiming",
    "WaitingPeriodResolutionCell",
    "WaitingPeriodResolutionCellError",
    "cells_compatible_for_dependency_join",
    "conservative_continuity_source",
    "continuity_resolution",
]
