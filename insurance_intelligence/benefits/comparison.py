"""Deterministic factual comparison of normalized benefit projections.

This module compares canonical projections only. It does not rank products,
recommend a product, infer entitlement, assess claims, or generate a
customer-facing answer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.normalization import (
    BenefitComparisonProjection,
    CanonicalComparisonMechanic,
)


class BenefitComparisonError(ValueError):
    """Raised when normalized projections cannot be compared safely."""


class ComparisonDimensionStatus(str, Enum):
    SHARED = "SHARED"
    DIFFERENT = "DIFFERENT"
    BLOCKED = "BLOCKED"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"


@dataclass(frozen=True)
class ComparisonSideIdentity:
    implementation_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "implementation_id",
            "insurer_id",
            "product_id",
            "product_variant_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise BenefitComparisonError(f"{field_name} must be non-empty text")
            object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True)
class ComparisonDimension:
    dimension_id: str
    status: ComparisonDimensionStatus
    left_value: object | None
    right_value: object | None
    unit: str | None
    left_source_dimension_ids: tuple[str, ...]
    right_source_dimension_ids: tuple[str, ...]
    left_evidence_reference_ids: tuple[str, ...]
    right_evidence_reference_ids: tuple[str, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dimension_id, str) or not self.dimension_id.strip():
            raise BenefitComparisonError("dimension_id must be non-empty text")
        object.__setattr__(self, "dimension_id", self.dimension_id.strip())
        if not isinstance(self.status, ComparisonDimensionStatus):
            raise BenefitComparisonError("status must be a ComparisonDimensionStatus")
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise BenefitComparisonError("unit must be non-empty text or None")
        if self.reason is not None and (not isinstance(self.reason, str) or not self.reason.strip()):
            raise BenefitComparisonError("reason must be non-empty text or None")


@dataclass(frozen=True)
class NormalizedBenefitComparisonResult:
    concept_id: str
    left: ComparisonSideIdentity
    right: ComparisonSideIdentity
    dimensions: tuple[ComparisonDimension, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.concept_id, str) or not self.concept_id.strip():
            raise BenefitComparisonError("concept_id must be non-empty text")
        object.__setattr__(self, "concept_id", self.concept_id.strip())
        if not isinstance(self.left, ComparisonSideIdentity):
            raise BenefitComparisonError("left must be a ComparisonSideIdentity")
        if not isinstance(self.right, ComparisonSideIdentity):
            raise BenefitComparisonError("right must be a ComparisonSideIdentity")
        if self.left.implementation_id == self.right.implementation_id:
            raise BenefitComparisonError("left and right implementation identities must differ")
        if not isinstance(self.dimensions, tuple) or not self.dimensions:
            raise BenefitComparisonError("dimensions must be a non-empty tuple")
        if not all(isinstance(item, ComparisonDimension) for item in self.dimensions):
            raise BenefitComparisonError("dimensions must contain ComparisonDimension values")
        dimension_ids = tuple(item.dimension_id for item in self.dimensions)
        if dimension_ids != tuple(sorted(dimension_ids)):
            raise BenefitComparisonError("dimensions must be deterministically ordered")
        if len(set(dimension_ids)) != len(dimension_ids):
            raise BenefitComparisonError("dimension ids must be unique")
        if not isinstance(self.limitations, tuple) or not self.limitations:
            raise BenefitComparisonError("limitations must be a non-empty tuple")

    def dimensions_with_status(
        self, status: ComparisonDimensionStatus
    ) -> tuple[ComparisonDimension, ...]:
        if not isinstance(status, ComparisonDimensionStatus):
            raise BenefitComparisonError("status must be a ComparisonDimensionStatus")
        return tuple(item for item in self.dimensions if item.status is status)

    @property
    def shared_dimensions(self) -> tuple[ComparisonDimension, ...]:
        return self.dimensions_with_status(ComparisonDimensionStatus.SHARED)

    @property
    def different_dimensions(self) -> tuple[ComparisonDimension, ...]:
        return self.dimensions_with_status(ComparisonDimensionStatus.DIFFERENT)

    @property
    def blocked_dimensions(self) -> tuple[ComparisonDimension, ...]:
        return self.dimensions_with_status(ComparisonDimensionStatus.BLOCKED)

    @property
    def left_only_dimensions(self) -> tuple[ComparisonDimension, ...]:
        return self.dimensions_with_status(ComparisonDimensionStatus.LEFT_ONLY)

    @property
    def right_only_dimensions(self) -> tuple[ComparisonDimension, ...]:
        return self.dimensions_with_status(ComparisonDimensionStatus.RIGHT_ONLY)


_DEFAULT_LIMITATIONS = (
    "This result compares only mechanics present in the canonical projections.",
    "A factual difference is not a ranking, recommendation, suitability conclusion, or entitlement decision.",
    "One-sided dimensions are disclosed but not treated as evidence that either product is superior.",
    "Policy schedules, endorsements, eligibility conditions, and claim facts remain outside this comparison result.",
)


def _identity(projection: BenefitComparisonProjection) -> ComparisonSideIdentity:
    return ComparisonSideIdentity(
        implementation_id=projection.implementation_id,
        insurer_id=projection.insurer_id,
        product_id=projection.product_id,
        product_variant_id=projection.product_variant_id,
    )


def _evidence(mechanic: CanonicalComparisonMechanic | None) -> tuple[str, ...]:
    return () if mechanic is None else mechanic.evidence_reference_ids


def _sources(mechanic: CanonicalComparisonMechanic | None) -> tuple[str, ...]:
    return () if mechanic is None else mechanic.source_dimension_ids


def _compare_dimension(
    dimension_id: str,
    left: CanonicalComparisonMechanic | None,
    right: CanonicalComparisonMechanic | None,
) -> ComparisonDimension:
    if left is None:
        assert right is not None
        return ComparisonDimension(
            dimension_id=dimension_id,
            status=ComparisonDimensionStatus.RIGHT_ONLY,
            left_value=None,
            right_value=right.value,
            unit=right.unit,
            left_source_dimension_ids=(),
            right_source_dimension_ids=right.source_dimension_ids,
            left_evidence_reference_ids=(),
            right_evidence_reference_ids=right.evidence_reference_ids,
            reason="dimension is present only in the right canonical projection",
        )
    if right is None:
        return ComparisonDimension(
            dimension_id=dimension_id,
            status=ComparisonDimensionStatus.LEFT_ONLY,
            left_value=left.value,
            right_value=None,
            unit=left.unit,
            left_source_dimension_ids=left.source_dimension_ids,
            right_source_dimension_ids=(),
            left_evidence_reference_ids=left.evidence_reference_ids,
            right_evidence_reference_ids=(),
            reason="dimension is present only in the left canonical projection",
        )
    if left.unit != right.unit:
        return ComparisonDimension(
            dimension_id=dimension_id,
            status=ComparisonDimensionStatus.BLOCKED,
            left_value=left.value,
            right_value=right.value,
            unit=None,
            left_source_dimension_ids=left.source_dimension_ids,
            right_source_dimension_ids=right.source_dimension_ids,
            left_evidence_reference_ids=left.evidence_reference_ids,
            right_evidence_reference_ids=right.evidence_reference_ids,
            reason=f"canonical units differ: left={left.unit!r}, right={right.unit!r}",
        )
    status = (
        ComparisonDimensionStatus.SHARED
        if left.value == right.value
        else ComparisonDimensionStatus.DIFFERENT
    )
    return ComparisonDimension(
        dimension_id=dimension_id,
        status=status,
        left_value=left.value,
        right_value=right.value,
        unit=left.unit,
        left_source_dimension_ids=_sources(left),
        right_source_dimension_ids=_sources(right),
        left_evidence_reference_ids=_evidence(left),
        right_evidence_reference_ids=_evidence(right),
    )


def compare_normalized_benefits(
    left: BenefitComparisonProjection,
    right: BenefitComparisonProjection,
) -> NormalizedBenefitComparisonResult:
    """Return a deterministic factual comparison of two canonical projections."""

    if not isinstance(left, BenefitComparisonProjection):
        raise BenefitComparisonError("left must be a BenefitComparisonProjection")
    if not isinstance(right, BenefitComparisonProjection):
        raise BenefitComparisonError("right must be a BenefitComparisonProjection")
    if left.implementation_id == right.implementation_id:
        raise BenefitComparisonError("cannot compare an implementation with itself")
    if left.concept_id != right.concept_id:
        raise BenefitComparisonError("normalized projections must share one concept_id")

    dimension_ids = tuple(sorted(set(left.mechanics) | set(right.mechanics)))
    dimensions = tuple(
        _compare_dimension(
            dimension_id,
            left.mechanics.get(dimension_id),
            right.mechanics.get(dimension_id),
        )
        for dimension_id in dimension_ids
    )

    return NormalizedBenefitComparisonResult(
        concept_id=left.concept_id,
        left=_identity(left),
        right=_identity(right),
        dimensions=dimensions,
        limitations=_DEFAULT_LIMITATIONS,
    )


__all__ = [
    "BenefitComparisonError",
    "ComparisonDimension",
    "ComparisonDimensionStatus",
    "ComparisonSideIdentity",
    "NormalizedBenefitComparisonResult",
    "compare_normalized_benefits",
]
