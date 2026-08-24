"""Generic semantics for personal / underwriting-specific waiting periods.

This module represents a product-level underwriting rule without manufacturing a
customer-specific waiting-period value. It is intentionally separate from the
resolved scalar ``WaitingPeriodMechanic`` because wording such as "up to 48 months"
is a maximum bound whose concrete duration and affected conditions depend on an
individual insured person's underwriting outcome.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodDurationUnit,
    WaitingPeriodStartBasis,
)


class PersonalUnderwritingWaitingPeriodError(ValueError):
    """Raised when the personal underwriting waiting-period contract is unsafe."""


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonalUnderwritingWaitingPeriodError(f"{label} must be non-empty text")
    return value.strip()


def _text_tuple(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise PersonalUnderwritingWaitingPeriodError(f"{label} must be a tuple")
    cleaned = tuple(_text(item, f"{label}[]") for item in value)
    if not cleaned:
        raise PersonalUnderwritingWaitingPeriodError(f"{label} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise PersonalUnderwritingWaitingPeriodError(f"{label} must not contain duplicates")
    return cleaned


@dataclass(frozen=True)
class PersonalUnderwritingWaitingPeriodMechanic:
    """Product-level rule for an underwriting-assigned personal waiting period.

    ``maximum_duration_value`` is an upper bound, not a resolved customer value.
    ``instance_resolution_required`` is intentionally fixed to True so this contract
    can never answer which conditions or duration apply to a particular insured
    person without separate policy-instance evidence.
    """

    maximum_duration_value: int
    maximum_duration_unit: WaitingPeriodDurationUnit
    start_basis: WaitingPeriodStartBasis
    applies_to: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    instance_resolution_dependency: str
    instance_resolution_required: bool = True
    semantic_variant: str = "PERSONAL_UNDERWRITING_SPECIFIC"
    scope_type: str = "INSURED_PERSON_CONDITION_SCOPED"
    duration_semantics: str = "MAXIMUM_BOUND"

    def __post_init__(self) -> None:
        if type(self.maximum_duration_value) is not int or self.maximum_duration_value <= 0:
            raise PersonalUnderwritingWaitingPeriodError(
                "maximum_duration_value must be a positive integer"
            )
        if not isinstance(self.maximum_duration_unit, WaitingPeriodDurationUnit):
            raise PersonalUnderwritingWaitingPeriodError(
                "maximum_duration_unit must be a WaitingPeriodDurationUnit"
            )
        if not isinstance(self.start_basis, WaitingPeriodStartBasis):
            raise PersonalUnderwritingWaitingPeriodError(
                "start_basis must be a WaitingPeriodStartBasis"
            )
        object.__setattr__(self, "applies_to", _text_tuple(self.applies_to, "applies_to"))
        object.__setattr__(
            self,
            "evidence_reference_ids",
            _text_tuple(self.evidence_reference_ids, "evidence_reference_ids"),
        )
        object.__setattr__(
            self,
            "instance_resolution_dependency",
            _text(self.instance_resolution_dependency, "instance_resolution_dependency"),
        )
        if self.instance_resolution_required is not True:
            raise PersonalUnderwritingWaitingPeriodError(
                "personal underwriting waiting periods must require instance resolution"
            )
        if self.semantic_variant != "PERSONAL_UNDERWRITING_SPECIFIC":
            raise PersonalUnderwritingWaitingPeriodError(
                "semantic_variant must remain PERSONAL_UNDERWRITING_SPECIFIC"
            )
        if self.scope_type != "INSURED_PERSON_CONDITION_SCOPED":
            raise PersonalUnderwritingWaitingPeriodError(
                "scope_type must remain INSURED_PERSON_CONDITION_SCOPED"
            )
        if self.duration_semantics != "MAXIMUM_BOUND":
            raise PersonalUnderwritingWaitingPeriodError(
                "duration_semantics must remain MAXIMUM_BOUND"
            )


__all__ = [
    "PersonalUnderwritingWaitingPeriodError",
    "PersonalUnderwritingWaitingPeriodMechanic",
]
