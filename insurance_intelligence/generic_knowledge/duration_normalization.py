"""Exact duration-unit normalization for governed insurance semantics.

This module intentionally supports only conversions with a deterministic integer ratio that do
not require calendar/day-count assumptions. It must not be used to calculate waiting-period
expiry dates or translate years/months into days.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError


class DurationNormalizationError(GenericKnowledgeContractError):
    """Raised when a duration cannot be normalized without calendar assumptions."""


class DurationUnit(str, Enum):
    DAYS = "DAYS"
    MONTHS = "MONTHS"
    YEARS = "YEARS"


@dataclass(frozen=True)
class NormalizedDuration:
    value: int
    unit: DurationUnit

    def __post_init__(self) -> None:
        if type(self.value) is not int or self.value < 0:
            raise DurationNormalizationError("value must be a non-negative integer")
        if not isinstance(self.unit, DurationUnit):
            raise DurationNormalizationError("unit must be DurationUnit")


def normalize_duration(value: int, source_unit: DurationUnit, target_unit: DurationUnit) -> NormalizedDuration:
    """Normalize only exact commensurable YEAR/MONTH durations.

    DAYS intentionally cannot be converted to or from MONTHS/YEARS because such conversion would
    require a calendar or day-count convention. Identity conversion is always allowed.
    """
    if type(value) is not int or value < 0:
        raise DurationNormalizationError("value must be a non-negative integer")
    if not isinstance(source_unit, DurationUnit) or not isinstance(target_unit, DurationUnit):
        raise DurationNormalizationError("source_unit and target_unit must be DurationUnit")
    if source_unit is target_unit:
        return NormalizedDuration(value=value, unit=target_unit)

    if source_unit is DurationUnit.YEARS and target_unit is DurationUnit.MONTHS:
        return NormalizedDuration(value=value * 12, unit=target_unit)
    if source_unit is DurationUnit.MONTHS and target_unit is DurationUnit.YEARS:
        if value % 12:
            raise DurationNormalizationError(
                "MONTHS to YEARS requires an exact whole-year integer ratio"
            )
        return NormalizedDuration(value=value // 12, unit=target_unit)

    raise DurationNormalizationError(
        "duration conversion requiring calendar/day-count assumptions is unsupported"
    )


__all__ = [
    "DurationNormalizationError",
    "DurationUnit",
    "NormalizedDuration",
    "normalize_duration",
]
