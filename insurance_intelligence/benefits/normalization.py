"""Canonical comparison projections for governed benefit mechanics.

This module creates comparison-safe projections without mutating or replacing
source-backed catalogue records. It currently supports the governed restoration
benefit implementations used by MO-025. It does not compare values, rank,
recommend, infer entitlement, or generate customer answers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping

from insurance_intelligence.benefits.catalogue import RESTORATION_CONCEPT_ID
from insurance_intelligence.benefits.contracts import (
    BenefitMechanic,
    ProductBenefitImplementation,
)


class MechanicNormalizationError(ValueError):
    """Raised when a governed implementation cannot be safely normalized."""


class RestorationFrequencyType(str, Enum):
    FINITE = "FINITE"
    UNLIMITED = "UNLIMITED"


@dataclass(frozen=True)
class CanonicalComparisonMechanic:
    dimension_id: str
    value: object
    unit: str | None
    source_dimension_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.dimension_id, str) or not self.dimension_id.strip():
            raise MechanicNormalizationError("dimension_id must be non-empty text")
        object.__setattr__(self, "dimension_id", self.dimension_id.strip())
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise MechanicNormalizationError("unit must be non-empty text or None")
        if self.unit is not None:
            object.__setattr__(self, "unit", self.unit.strip())
        if not isinstance(self.source_dimension_ids, tuple) or not self.source_dimension_ids:
            raise MechanicNormalizationError("source_dimension_ids must be a non-empty tuple")
        if not isinstance(self.evidence_reference_ids, tuple) or not self.evidence_reference_ids:
            raise MechanicNormalizationError("evidence_reference_ids must be a non-empty tuple")


@dataclass(frozen=True)
class BenefitComparisonProjection:
    implementation_id: str
    concept_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str
    mechanics: Mapping[str, CanonicalComparisonMechanic]

    def __post_init__(self) -> None:
        for field_name in (
            "implementation_id",
            "concept_id",
            "insurer_id",
            "product_id",
            "product_variant_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise MechanicNormalizationError(f"{field_name} must be non-empty text")
            object.__setattr__(self, field_name, value.strip())
        mechanics = dict(self.mechanics)
        if not mechanics:
            raise MechanicNormalizationError("mechanics must not be empty")
        if any(key != mechanic.dimension_id for key, mechanic in mechanics.items()):
            raise MechanicNormalizationError("mechanic mapping keys must match dimension_id")
        object.__setattr__(self, "mechanics", MappingProxyType(mechanics))

    @property
    def dimension_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.mechanics))


_PASSTHROUGH_DIMENSIONS = (
    "trigger_requirement",
    "trigger_timing",
    "same_hospitalization_use",
    "subsequent_hospitalization_use",
    "covered_section_scope",
    "policy_year_reset",
    "floater_operation",
)


def _mechanic_map(
    implementation: ProductBenefitImplementation,
) -> dict[str, BenefitMechanic]:
    return {mechanic.dimension_id: mechanic for mechanic in implementation.mechanics}


def _canonical_mechanic(
    *,
    dimension_id: str,
    value: object,
    unit: str | None,
    source_mechanics: tuple[BenefitMechanic, ...],
) -> CanonicalComparisonMechanic:
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for mechanic in source_mechanics
            for evidence_id in mechanic.evidence_reference_ids
        )
    )
    return CanonicalComparisonMechanic(
        dimension_id=dimension_id,
        value=value,
        unit=unit,
        source_dimension_ids=tuple(mechanic.dimension_id for mechanic in source_mechanics),
        evidence_reference_ids=evidence_ids,
    )


def _normalize_restoration_amount(
    mechanics: Mapping[str, BenefitMechanic],
) -> CanonicalComparisonMechanic:
    source = mechanics.get("restoration_percentage")
    if source is None:
        raise MechanicNormalizationError("restoration_percentage is required")
    if source.value != 100:
        raise MechanicNormalizationError(
            "only source-backed 100 percent restoration implementations are currently supported"
        )
    if source.unit not in {
        "percent_of_basic_sum_insured",
        "percent_of_base_sum_insured_per_activation",
    }:
        raise MechanicNormalizationError(
            f"unsupported restoration percentage unit: {source.unit!r}"
        )
    return _canonical_mechanic(
        dimension_id="restoration_amount_percentage_per_activation",
        value=100,
        unit="percent_of_governed_base_sum_insured",
        source_mechanics=(source,),
    )


def _normalize_restoration_frequency(
    mechanics: Mapping[str, BenefitMechanic],
) -> tuple[CanonicalComparisonMechanic, CanonicalComparisonMechanic]:
    source = mechanics.get("restoration_count_per_policy_period")
    if source is None:
        raise MechanicNormalizationError("restoration_count_per_policy_period is required")

    if isinstance(source.value, int) and not isinstance(source.value, bool):
        if source.value < 1:
            raise MechanicNormalizationError("finite restoration count must be positive")
        frequency_type = RestorationFrequencyType.FINITE.value
        frequency_count: int | None = source.value
    elif source.value == "unlimited_during_policy_year":
        frequency_type = RestorationFrequencyType.UNLIMITED.value
        frequency_count = None
    else:
        raise MechanicNormalizationError(
            f"unsupported restoration frequency representation: {source.value!r}"
        )

    return (
        _canonical_mechanic(
            dimension_id="restoration_frequency_type",
            value=frequency_type,
            unit=None,
            source_mechanics=(source,),
        ),
        _canonical_mechanic(
            dimension_id="restoration_frequency_count",
            value=frequency_count,
            unit="activations_per_policy_period",
            source_mechanics=(source,),
        ),
    )


def normalize_for_comparison(
    implementation: ProductBenefitImplementation,
) -> BenefitComparisonProjection:
    """Create a canonical, evidence-preserving comparison projection."""

    if not isinstance(implementation, ProductBenefitImplementation):
        raise MechanicNormalizationError(
            "implementation must be a ProductBenefitImplementation"
        )
    if implementation.concept_id != RESTORATION_CONCEPT_ID:
        raise MechanicNormalizationError(
            f"unsupported concept for normalization: {implementation.concept_id}"
        )
    if not implementation.is_governed_for_use:
        raise MechanicNormalizationError(
            "implementation must be approved and published before normalization"
        )

    mechanics = _mechanic_map(implementation)
    normalized: dict[str, CanonicalComparisonMechanic] = {}

    amount = _normalize_restoration_amount(mechanics)
    normalized[amount.dimension_id] = amount

    frequency_type, frequency_count = _normalize_restoration_frequency(mechanics)
    normalized[frequency_type.dimension_id] = frequency_type
    normalized[frequency_count.dimension_id] = frequency_count

    for dimension_id in _PASSTHROUGH_DIMENSIONS:
        source = mechanics.get(dimension_id)
        if source is None:
            continue
        normalized[dimension_id] = _canonical_mechanic(
            dimension_id=dimension_id,
            value=source.value,
            unit=source.unit,
            source_mechanics=(source,),
        )

    for dimension_id in (
        "first_claim_use",
        "partial_restoration_use",
        "maximum_liability_per_claim_percentage",
        "utilization_sequence",
        "same_illness_use",
        "relapse_window_days",
        "carry_over_between_policy_years",
    ):
        source = mechanics.get(dimension_id)
        if source is None:
            continue
        normalized[dimension_id] = _canonical_mechanic(
            dimension_id=dimension_id,
            value=source.value,
            unit=source.unit,
            source_mechanics=(source,),
        )

    return BenefitComparisonProjection(
        implementation_id=implementation.implementation_id,
        concept_id=implementation.concept_id,
        insurer_id=implementation.insurer_id,
        product_id=implementation.product_id,
        product_variant_id=implementation.product_variant_id,
        mechanics=normalized,
    )


__all__ = [
    "BenefitComparisonProjection",
    "CanonicalComparisonMechanic",
    "MechanicNormalizationError",
    "RestorationFrequencyType",
    "normalize_for_comparison",
]
