"""Generic dependency-resolution contracts for MO-028B.G11.C2.

C1 computes the resolution state of one semantic value cell. C2 composes those states across
semantic dependencies without performing insurance-specific arithmetic.

Two dependency modes are intentionally distinct:
- REQUIRED_INPUT: every dependency must resolve before an effective result can resolve.
- CONDITIONAL_MODIFIER: a governed base remains usable conservatively while modifier
  applicability is unresolved.

Relationships default to NONE. Product identity must never influence propagation.
"""
from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from insurance_intelligence.generic_knowledge.contracts import ApplicabilityKey
from insurance_intelligence.generic_knowledge.resolution_status import (
    ComputedResolution,
    ResolutionContractError,
    ResolutionSeverity,
    ResolutionStatus,
    most_blocking_status,
    resolution_severity,
)


class DependencyResolutionError(ResolutionContractError):
    """Raised when dependency-resolution contracts violate generic invariants."""


class ResolutionDependencyMode(str, Enum):
    NONE = "NONE"
    REQUIRED_INPUT = "REQUIRED_INPUT"
    CONDITIONAL_MODIFIER = "CONDITIONAL_MODIFIER"


class ModifierDirection(str, Enum):
    REDUCES = "REDUCES"
    WAIVES = "WAIVES"
    REPLACES = "REPLACES"
    LIMITS = "LIMITS"


class EffectiveDependencyState(str, Enum):
    FULLY_RESOLVED = "FULLY_RESOLVED"
    REQUIRED_INPUT_UNRESOLVED = "REQUIRED_INPUT_UNRESOLVED"
    CONDITIONAL_RANGE = "CONDITIONAL_RANGE"
    CONSERVATIVE_BASE_APPLIES = "CONSERVATIVE_BASE_APPLIES"
    VALIDATION_CONFLICT = "VALIDATION_CONFLICT"


@dataclass(frozen=True)
class ResolutionOperand:
    operand_id: str
    resolution: ComputedResolution
    applicability: ApplicabilityKey
    resolution_cell_identity: Hashable | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.operand_id, str) or not self.operand_id.strip():
            raise DependencyResolutionError("operand_id must be non-empty text")
        object.__setattr__(self, "operand_id", self.operand_id.strip())
        if not isinstance(self.resolution, ComputedResolution):
            raise DependencyResolutionError("resolution must be ComputedResolution")
        if not isinstance(self.applicability, ApplicabilityKey):
            raise DependencyResolutionError("applicability must be ApplicabilityKey")
        if self.resolution_cell_identity is not None and not isinstance(
            self.resolution_cell_identity, Hashable
        ):
            raise DependencyResolutionError("resolution_cell_identity must be hashable or None")


@dataclass(frozen=True)
class OperandResolutionCause:
    operand_id: str
    status: ResolutionStatus
    severity: ResolutionSeverity
    primary: bool

    def __post_init__(self) -> None:
        if not isinstance(self.operand_id, str) or not self.operand_id.strip():
            raise DependencyResolutionError("operand_id must be non-empty text")
        if not isinstance(self.status, ResolutionStatus):
            raise DependencyResolutionError("status must be ResolutionStatus")
        if not isinstance(self.severity, ResolutionSeverity):
            raise DependencyResolutionError("severity must be ResolutionSeverity")
        if self.severity is not resolution_severity(self.status):
            raise DependencyResolutionError("cause severity must match status")
        if type(self.primary) is not bool:
            raise DependencyResolutionError("primary must be boolean")


@dataclass(frozen=True)
class EffectiveDependencyResolution:
    mode: ResolutionDependencyMode
    effective_state: EffectiveDependencyState
    base_resolution: ComputedResolution | None
    dependency_resolution: ComputedResolution | None
    modifier_direction: ModifierDirection | None
    causes: tuple[OperandResolutionCause, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ResolutionDependencyMode):
            raise DependencyResolutionError("mode must be ResolutionDependencyMode")
        if not isinstance(self.effective_state, EffectiveDependencyState):
            raise DependencyResolutionError("effective_state must be EffectiveDependencyState")
        if self.base_resolution is not None and not isinstance(self.base_resolution, ComputedResolution):
            raise DependencyResolutionError("base_resolution must be ComputedResolution or None")
        if self.dependency_resolution is not None and not isinstance(self.dependency_resolution, ComputedResolution):
            raise DependencyResolutionError("dependency_resolution must be ComputedResolution or None")
        if self.modifier_direction is not None and not isinstance(self.modifier_direction, ModifierDirection):
            raise DependencyResolutionError("modifier_direction must be ModifierDirection or None")
        if any(not isinstance(cause, OperandResolutionCause) for cause in self.causes):
            raise DependencyResolutionError("causes must contain OperandResolutionCause values")


def _normalize_operands(operands: Iterable[ResolutionOperand]) -> tuple[ResolutionOperand, ...]:
    normalized = tuple(operands)
    if not normalized:
        raise DependencyResolutionError("operands must not be empty")
    if any(not isinstance(operand, ResolutionOperand) for operand in normalized):
        raise DependencyResolutionError("operands must contain ResolutionOperand values")
    ids = tuple(operand.operand_id for operand in normalized)
    if len(set(ids)) != len(ids):
        raise DependencyResolutionError("operand IDs must be unique")
    return normalized


def _same_applicability_cell(operands: tuple[ResolutionOperand, ...]) -> bool:
    first = operands[0]
    return all(
        operand.applicability == first.applicability
        and operand.resolution_cell_identity == first.resolution_cell_identity
        for operand in operands[1:]
    )


def _validation_conflict() -> ComputedResolution:
    return ComputedResolution(
        status=ResolutionStatus.VALIDATION_CONFLICT,
        severity=ResolutionSeverity.VALIDATION_BLOCKED,
        causes=(ResolutionStatus.VALIDATION_CONFLICT,),
    )


def _operand_wrapper_status(status: ResolutionStatus) -> ResolutionStatus:
    severity = resolution_severity(status)
    if severity is ResolutionSeverity.RESOLVED:
        return ResolutionStatus.RESOLVED
    if severity is ResolutionSeverity.INSTANCE_BOUND:
        return ResolutionStatus.OPERAND_INSTANCE_BOUND
    if severity is ResolutionSeverity.GOVERNANCE_BLOCKED:
        return ResolutionStatus.OPERAND_GOVERNANCE_BLOCKED
    if severity is ResolutionSeverity.REPRESENTATIONALLY_BLOCKED:
        return ResolutionStatus.OPERAND_REPRESENTATIONALLY_BLOCKED
    return ResolutionStatus.VALIDATION_CONFLICT


def _causes(operands: tuple[ResolutionOperand, ...], dominant: ResolutionSeverity) -> tuple[OperandResolutionCause, ...]:
    # Stable input ordering is preserved. All non-resolved causes are retained; causes in the
    # dominant severity class are marked primary.
    return tuple(
        OperandResolutionCause(
            operand_id=operand.operand_id,
            status=operand.resolution.status,
            severity=operand.resolution.severity,
            primary=operand.resolution.severity is dominant,
        )
        for operand in operands
        if operand.resolution.status is not ResolutionStatus.RESOLVED
    )


def resolve_required_inputs(operands: Iterable[ResolutionOperand]) -> EffectiveDependencyResolution:
    """Resolve a dependency whose effective result requires every operand.

    No value arithmetic occurs here. This function only answers whether an effective result may
    be produced and preserves why not.
    """
    normalized = _normalize_operands(operands)
    if not _same_applicability_cell(normalized):
        conflict = _validation_conflict()
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.REQUIRED_INPUT,
            effective_state=EffectiveDependencyState.VALIDATION_CONFLICT,
            base_resolution=None,
            dependency_resolution=conflict,
            modifier_direction=None,
            causes=(),
        )

    joined = most_blocking_status(operand.resolution.status for operand in normalized)
    if joined.status is ResolutionStatus.RESOLVED:
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.REQUIRED_INPUT,
            effective_state=EffectiveDependencyState.FULLY_RESOLVED,
            base_resolution=None,
            dependency_resolution=joined,
            modifier_direction=None,
            causes=(),
        )

    wrapper_status = _operand_wrapper_status(joined.status)
    propagated = ComputedResolution(
        status=wrapper_status,
        severity=resolution_severity(wrapper_status),
        causes=tuple(operand.resolution.status for operand in normalized),
    )
    effective_state = (
        EffectiveDependencyState.VALIDATION_CONFLICT
        if wrapper_status is ResolutionStatus.VALIDATION_CONFLICT
        else EffectiveDependencyState.REQUIRED_INPUT_UNRESOLVED
    )
    return EffectiveDependencyResolution(
        mode=ResolutionDependencyMode.REQUIRED_INPUT,
        effective_state=effective_state,
        base_resolution=None,
        dependency_resolution=propagated,
        modifier_direction=None,
        causes=_causes(normalized, joined.severity),
    )


def resolve_conditional_modifier(
    *,
    base: ResolutionOperand,
    modifier: ResolutionOperand,
    direction: ModifierDirection,
) -> EffectiveDependencyResolution:
    """Resolve a conditional modifier without erasing a known conservative base.

    C2 does not calculate modified values. It classifies what may safely be said while modifier
    applicability is unresolved.
    """
    if not isinstance(base, ResolutionOperand) or not isinstance(modifier, ResolutionOperand):
        raise DependencyResolutionError("base and modifier must be ResolutionOperand values")
    if not isinstance(direction, ModifierDirection):
        raise DependencyResolutionError("direction must be ModifierDirection")
    if base.operand_id == modifier.operand_id:
        raise DependencyResolutionError("base and modifier operand IDs must differ")
    if (
        base.applicability != modifier.applicability
        or base.resolution_cell_identity != modifier.resolution_cell_identity
    ):
        conflict = _validation_conflict()
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
            effective_state=EffectiveDependencyState.VALIDATION_CONFLICT,
            base_resolution=base.resolution,
            dependency_resolution=conflict,
            modifier_direction=direction,
            causes=(),
        )

    # A conditional relationship cannot rescue an unresolved base. Until the base itself is
    # resolved, effective-value resolution remains a required-input problem.
    if base.resolution.status is not ResolutionStatus.RESOLVED:
        required = resolve_required_inputs((base,))
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
            effective_state=required.effective_state,
            base_resolution=base.resolution,
            dependency_resolution=required.dependency_resolution,
            modifier_direction=direction,
            causes=required.causes,
        )

    if modifier.resolution.status is ResolutionStatus.RESOLVED:
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
            effective_state=EffectiveDependencyState.FULLY_RESOLVED,
            base_resolution=base.resolution,
            dependency_resolution=modifier.resolution,
            modifier_direction=direction,
            causes=(),
        )

    if modifier.resolution.status is ResolutionStatus.VALIDATION_CONFLICT:
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
            effective_state=EffectiveDependencyState.VALIDATION_CONFLICT,
            base_resolution=base.resolution,
            dependency_resolution=modifier.resolution,
            modifier_direction=direction,
            causes=_causes((modifier,), modifier.resolution.severity),
        )

    # Only an instance-bound modifier gets conservative/bounded treatment. Governance or
    # representational blocks mean PolicyScna does not yet know enough about the modifier itself
    # to safely classify its effect.
    if modifier.resolution.severity is ResolutionSeverity.INSTANCE_BOUND:
        state = (
            EffectiveDependencyState.CONSERVATIVE_BASE_APPLIES
            if direction in (ModifierDirection.WAIVES, ModifierDirection.REPLACES)
            else EffectiveDependencyState.CONDITIONAL_RANGE
        )
        return EffectiveDependencyResolution(
            mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
            effective_state=state,
            base_resolution=base.resolution,
            dependency_resolution=modifier.resolution,
            modifier_direction=direction,
            causes=_causes((modifier,), modifier.resolution.severity),
        )

    required = resolve_required_inputs((modifier,))
    return EffectiveDependencyResolution(
        mode=ResolutionDependencyMode.CONDITIONAL_MODIFIER,
        effective_state=required.effective_state,
        base_resolution=base.resolution,
        dependency_resolution=required.dependency_resolution,
        modifier_direction=direction,
        causes=required.causes,
    )


def validate_dependency_path(path: Iterable[str], *, max_depth: int = 32) -> None:
    """Reject self/multi-node cycles without introducing a graph subsystem."""
    normalized = tuple(path)
    if not isinstance(max_depth, int) or max_depth < 1:
        raise DependencyResolutionError("max_depth must be a positive integer")
    if len(normalized) > max_depth:
        raise DependencyResolutionError("dependency path exceeds maximum depth")
    for node_id in normalized:
        if not isinstance(node_id, str) or not node_id.strip():
            raise DependencyResolutionError("dependency path IDs must be non-empty text")
    if len(set(normalized)) != len(normalized):
        raise DependencyResolutionError("dependency cycle detected")


__all__ = [
    "DependencyResolutionError",
    "EffectiveDependencyResolution",
    "EffectiveDependencyState",
    "ModifierDirection",
    "OperandResolutionCause",
    "ResolutionDependencyMode",
    "ResolutionOperand",
    "resolve_conditional_modifier",
    "resolve_required_inputs",
    "validate_dependency_path",
]
