"""Governed waiting-period semantic contracts for MO-028B.

These contracts describe policy mechanics only. They do not infer a product's
waiting period, determine medical eligibility, predict claim payment, or create
customer-specific recommendations. Product facts may enter runtime use only
through separately governed evidence-backed publications.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WaitingPeriodContractError(ValueError):
    """Raised when a waiting-period semantic contract violates an invariant."""


def _text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WaitingPeriodContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _text(value, field_name)


def _text_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise WaitingPeriodContractError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(item, f"{field_name}[]") for item in value)
    if len(cleaned) != len(set(cleaned)):
        raise WaitingPeriodContractError(f"{field_name} must not contain duplicates")
    return cleaned


class WaitingPeriodType(str, Enum):
    INITIAL = "INITIAL"
    SPECIFIC_DISEASE_PROCEDURE = "SPECIFIC_DISEASE_PROCEDURE"
    PRE_EXISTING_DISEASE = "PRE_EXISTING_DISEASE"
    MATERNITY = "MATERNITY"
    BABY_CARE = "BABY_CARE"


class WaitingPeriodDurationUnit(str, Enum):
    DAYS = "DAYS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


class WaitingPeriodStartBasis(str, Enum):
    POLICY_INCEPTION = "POLICY_INCEPTION"
    INSURED_PERSON_FIRST_COVERAGE = "INSURED_PERSON_FIRST_COVERAGE"
    CONTINUOUS_COVERAGE = "CONTINUOUS_COVERAGE"
    POLICY_SCHEDULE_DEFINED = "POLICY_SCHEDULE_DEFINED"
    INSURED_PERSON_ADDITION_DATE = "INSURED_PERSON_ADDITION_DATE"


class WaitingPeriodModificationType(str, Enum):
    WAIVER = "WAIVER"
    REDUCTION = "REDUCTION"
    CREDIT_FOR_CONTINUITY = "CREDIT_FOR_CONTINUITY"


@dataclass(frozen=True)
class WaitingPeriodModification:
    """A clause that can alter the base waiting-period duration or operation."""

    modification_type: WaitingPeriodModificationType
    condition: str
    resulting_duration_value: int | None = None
    resulting_duration_unit: WaitingPeriodDurationUnit | None = None
    evidence_reference_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.modification_type, WaitingPeriodModificationType):
            raise WaitingPeriodContractError(
                "modification_type must be a WaitingPeriodModificationType"
            )
        object.__setattr__(self, "condition", _text(self.condition, "condition"))
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids"),
        )
        if not self.evidence_reference_ids:
            raise WaitingPeriodContractError(
                "waiting-period modification requires evidence references"
            )

        has_value = self.resulting_duration_value is not None
        has_unit = self.resulting_duration_unit is not None
        if has_value != has_unit:
            raise WaitingPeriodContractError(
                "resulting duration value and unit must be provided together"
            )
        if has_value:
            if type(self.resulting_duration_value) is not int or self.resulting_duration_value < 0:
                raise WaitingPeriodContractError(
                    "resulting_duration_value must be a non-negative integer"
                )
            if not isinstance(self.resulting_duration_unit, WaitingPeriodDurationUnit):
                raise WaitingPeriodContractError(
                    "resulting_duration_unit must be a WaitingPeriodDurationUnit"
                )

        if self.modification_type is WaitingPeriodModificationType.WAIVER:
            if self.resulting_duration_value not in (None, 0):
                raise WaitingPeriodContractError(
                    "WAIVER may only omit duration or result in zero duration"
                )
        elif not has_value:
            raise WaitingPeriodContractError(
                f"{self.modification_type.value} requires a resulting duration"
            )


@dataclass(frozen=True)
class WaitingPeriodMechanic:
    """Typed semantic representation of one governed waiting-period clause."""

    waiting_period_type: WaitingPeriodType
    duration_value: int
    duration_unit: WaitingPeriodDurationUnit
    start_basis: WaitingPeriodStartBasis
    applies_to: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    exclusions_or_exceptions: tuple[str, ...] = ()
    modifications: tuple[WaitingPeriodModification, ...] = ()
    schedule_dependency: str | None = None
    continuity_dependency: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.waiting_period_type, WaitingPeriodType):
            raise WaitingPeriodContractError(
                "waiting_period_type must be a WaitingPeriodType"
            )
        if type(self.duration_value) is not int or self.duration_value < 0:
            raise WaitingPeriodContractError(
                "duration_value must be a non-negative integer"
            )
        if not isinstance(self.duration_unit, WaitingPeriodDurationUnit):
            raise WaitingPeriodContractError(
                "duration_unit must be a WaitingPeriodDurationUnit"
            )
        if not isinstance(self.start_basis, WaitingPeriodStartBasis):
            raise WaitingPeriodContractError(
                "start_basis must be a WaitingPeriodStartBasis"
            )

        object.__setattr__(self, "applies_to", _text_tuple(self.applies_to, "applies_to"))
        if not self.applies_to:
            raise WaitingPeriodContractError("applies_to must not be empty")
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids"),
        )
        if not self.evidence_reference_ids:
            raise WaitingPeriodContractError(
                "waiting-period mechanic requires evidence references"
            )
        object.__setattr__(
            self,
            "exclusions_or_exceptions",
            _text_tuple(self.exclusions_or_exceptions, "exclusions_or_exceptions"),
        )
        if not isinstance(self.modifications, tuple) or not all(
            type(item) is WaitingPeriodModification for item in self.modifications
        ):
            raise WaitingPeriodContractError(
                "modifications must contain exact WaitingPeriodModification values"
            )
        object.__setattr__(
            self,
            "schedule_dependency",
            _optional_text(self.schedule_dependency, "schedule_dependency"),
        )
        object.__setattr__(
            self,
            "continuity_dependency",
            _optional_text(self.continuity_dependency, "continuity_dependency"),
        )

        if self.start_basis is WaitingPeriodStartBasis.POLICY_SCHEDULE_DEFINED:
            if self.schedule_dependency is None:
                raise WaitingPeriodContractError(
                    "POLICY_SCHEDULE_DEFINED requires schedule_dependency"
                )
        if self.start_basis is WaitingPeriodStartBasis.CONTINUOUS_COVERAGE:
            if self.continuity_dependency is None:
                raise WaitingPeriodContractError(
                    "CONTINUOUS_COVERAGE requires continuity_dependency"
                )


__all__ = [
    "WaitingPeriodContractError",
    "WaitingPeriodDurationUnit",
    "WaitingPeriodMechanic",
    "WaitingPeriodModification",
    "WaitingPeriodModificationType",
    "WaitingPeriodStartBasis",
    "WaitingPeriodType",
]
