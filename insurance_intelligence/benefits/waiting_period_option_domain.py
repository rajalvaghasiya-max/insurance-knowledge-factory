"""Typed unresolved option domains for Schedule-selected waiting periods."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodContractError,
    WaitingPeriodDurationUnit,
    WaitingPeriodScopeType,
    WaitingPeriodType,
    WaitingPeriodValueSource,
)


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise WaitingPeriodContractError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(item, f"{field_name}[]") for item in value)
    if len(cleaned) != len(set(cleaned)):
        raise WaitingPeriodContractError(f"{field_name} must not contain duplicates")
    return cleaned


@dataclass(frozen=True, order=True)
class WaitingPeriodDurationOption:
    duration_value: int
    duration_unit: WaitingPeriodDurationUnit

    def __post_init__(self) -> None:
        if type(self.duration_value) is not int or self.duration_value < 0:
            raise WaitingPeriodContractError("duration_value must be a non-negative integer")
        if not isinstance(self.duration_unit, WaitingPeriodDurationUnit):
            raise WaitingPeriodContractError("duration_unit must be a WaitingPeriodDurationUnit")


@dataclass(frozen=True)
class WaitingPeriodDurationOptionDomain:
    """Authoritative unresolved Schedule-selectable waiting-period durations."""

    waiting_period_type: WaitingPeriodType
    options: tuple[WaitingPeriodDurationOption, ...]
    applies_to: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    schedule_dependency: str
    scope_type: WaitingPeriodScopeType = WaitingPeriodScopeType.POLICY_WIDE
    scope_reference: str | None = None
    value_source: WaitingPeriodValueSource = WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED

    def __post_init__(self) -> None:
        if not isinstance(self.waiting_period_type, WaitingPeriodType):
            raise WaitingPeriodContractError("waiting_period_type must be a WaitingPeriodType")
        if not isinstance(self.options, tuple) or not all(type(item) is WaitingPeriodDurationOption for item in self.options):
            raise WaitingPeriodContractError("options must contain exact WaitingPeriodDurationOption values")
        if len(self.options) < 2:
            raise WaitingPeriodContractError("unresolved option domain requires at least two duration options")
        if len(self.options) != len(set(self.options)):
            raise WaitingPeriodContractError("options must not contain duplicates")
        if len({item.duration_unit for item in self.options}) != 1:
            raise WaitingPeriodContractError("duration option domain must use one common duration unit")
        if tuple(sorted(self.options)) != self.options:
            raise WaitingPeriodContractError("options must be in deterministic ascending duration order")

        object.__setattr__(self, "applies_to", _text_tuple(self.applies_to, "applies_to"))
        if not self.applies_to:
            raise WaitingPeriodContractError("applies_to must not be empty")
        object.__setattr__(self, "evidence_reference_ids", _text_tuple(self.evidence_reference_ids, "evidence_reference_ids"))
        if not self.evidence_reference_ids:
            raise WaitingPeriodContractError("waiting-period option domain requires evidence references")
        object.__setattr__(self, "schedule_dependency", _text(self.schedule_dependency, "schedule_dependency"))

        if not isinstance(self.scope_type, WaitingPeriodScopeType):
            raise WaitingPeriodContractError("scope_type must be a WaitingPeriodScopeType")
        if self.scope_reference is not None:
            object.__setattr__(self, "scope_reference", _text(self.scope_reference, "scope_reference"))
        if self.scope_type is WaitingPeriodScopeType.BENEFIT_SCOPED and self.scope_reference is None:
            raise WaitingPeriodContractError("BENEFIT_SCOPED requires scope_reference")
        if self.scope_type is WaitingPeriodScopeType.POLICY_WIDE and self.scope_reference is not None:
            raise WaitingPeriodContractError("POLICY_WIDE must not define scope_reference")
        if self.value_source is not WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED:
            raise WaitingPeriodContractError("unresolved option domain must use POLICY_SCHEDULE_SELECTED value_source")


__all__ = ["WaitingPeriodDurationOption", "WaitingPeriodDurationOptionDomain"]
