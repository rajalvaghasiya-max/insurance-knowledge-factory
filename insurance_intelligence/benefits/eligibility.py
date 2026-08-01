"""Comparison eligibility gate for governed product-benefit implementations.

The gate determines whether two governed implementations can be compared safely
and meaningfully. It does not compare values, rank products, recommend a product,
decide entitlement, assess claims, or generate customer-facing answers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.contracts import (
    BenefitMechanic,
    ProductBenefitImplementation,
)


class ComparisonEligibilityError(ValueError):
    """Raised when an eligibility request is structurally invalid."""


class ComparisonEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    PARTIALLY_ELIGIBLE = "PARTIALLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


REQUIRED_COMPARISON_DIMENSIONS = (
    "restoration_percentage",
    "restoration_count_per_policy_period",
    "trigger_requirement",
    "same_hospitalization_use",
    "subsequent_hospitalization_use",
)

_MINIMUM_PARTIAL_OVERLAP = 3


@dataclass(frozen=True)
class ComparisonEligibilityRequest:
    left: ProductBenefitImplementation
    right: ProductBenefitImplementation
    as_of: date

    def __post_init__(self) -> None:
        if not isinstance(self.left, ProductBenefitImplementation):
            raise ComparisonEligibilityError("left must be a ProductBenefitImplementation")
        if not isinstance(self.right, ProductBenefitImplementation):
            raise ComparisonEligibilityError("right must be a ProductBenefitImplementation")
        if not isinstance(self.as_of, date):
            raise ComparisonEligibilityError("as_of must be a date")


@dataclass(frozen=True)
class ComparisonEligibilityResult:
    status: ComparisonEligibilityStatus
    as_of: date
    left_implementation_id: str
    right_implementation_id: str
    concept_id: str | None
    comparable_dimensions: tuple[str, ...]
    blocked_dimensions: tuple[str, ...]
    left_only_dimensions: tuple[str, ...]
    right_only_dimensions: tuple[str, ...]
    missing_required_left: tuple[str, ...]
    missing_required_right: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, ComparisonEligibilityStatus):
            raise ComparisonEligibilityError("status must be a ComparisonEligibilityStatus")
        if not isinstance(self.as_of, date):
            raise ComparisonEligibilityError("as_of must be a date")
        if not self.left_implementation_id.strip() or not self.right_implementation_id.strip():
            raise ComparisonEligibilityError("implementation identities must be non-empty")
        for field_name in (
            "comparable_dimensions",
            "blocked_dimensions",
            "left_only_dimensions",
            "right_only_dimensions",
            "missing_required_left",
            "missing_required_right",
            "reasons",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise ComparisonEligibilityError(f"{field_name} must be a tuple")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ComparisonEligibilityError(f"{field_name} must contain non-empty text")

    @property
    def may_compare(self) -> bool:
        return self.status in {
            ComparisonEligibilityStatus.ELIGIBLE,
            ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE,
        }

    @property
    def is_full_comparison(self) -> bool:
        return self.status is ComparisonEligibilityStatus.ELIGIBLE


def _mechanics_by_dimension(
    implementation: ProductBenefitImplementation,
) -> dict[str, BenefitMechanic]:
    return {mechanic.dimension_id: mechanic for mechanic in implementation.mechanics}


def evaluate_comparison_eligibility(
    request: ComparisonEligibilityRequest,
) -> ComparisonEligibilityResult:
    """Evaluate whether two governed implementations are safe to compare."""

    if not isinstance(request, ComparisonEligibilityRequest):
        raise ComparisonEligibilityError(
            "request must be a ComparisonEligibilityRequest"
        )

    left = request.left
    right = request.right
    reasons: list[str] = []

    hard_blocked = False
    concept_id: str | None = left.concept_id if left.concept_id == right.concept_id else None

    if left.implementation_id == right.implementation_id:
        hard_blocked = True
        reasons.append("comparison requires two distinct implementation identities")
    if left.concept_id != right.concept_id:
        hard_blocked = True
        reasons.append("implementations do not share the same canonical benefit concept")
    if not left.is_governed_for_use:
        hard_blocked = True
        reasons.append("left implementation is not approved and published for governed use")
    if not right.is_governed_for_use:
        hard_blocked = True
        reasons.append("right implementation is not approved and published for governed use")
    if not left.is_active(request.as_of):
        hard_blocked = True
        reasons.append("left implementation is not active on the requested effective date")
    if not right.is_active(request.as_of):
        hard_blocked = True
        reasons.append("right implementation is not active on the requested effective date")

    left_mechanics = _mechanics_by_dimension(left)
    right_mechanics = _mechanics_by_dimension(right)
    left_dimensions = set(left_mechanics)
    right_dimensions = set(right_mechanics)
    shared_dimensions = left_dimensions & right_dimensions

    blocked_dimensions = tuple(
        sorted(
            dimension
            for dimension in shared_dimensions
            if left_mechanics[dimension].value_type
            is not right_mechanics[dimension].value_type
            or left_mechanics[dimension].unit != right_mechanics[dimension].unit
        )
    )
    comparable_dimensions = tuple(sorted(shared_dimensions - set(blocked_dimensions)))
    left_only_dimensions = tuple(sorted(left_dimensions - right_dimensions))
    right_only_dimensions = tuple(sorted(right_dimensions - left_dimensions))
    required = set(REQUIRED_COMPARISON_DIMENSIONS)
    missing_required_left = tuple(sorted(required - left_dimensions))
    missing_required_right = tuple(sorted(required - right_dimensions))
    blocked_required = required & set(blocked_dimensions)
    comparable_required = required & set(comparable_dimensions)

    if blocked_dimensions:
        reasons.append(
            "shared dimensions with incompatible value types or units are blocked"
        )
    if missing_required_left:
        reasons.append("left implementation is missing required comparison dimensions")
    if missing_required_right:
        reasons.append("right implementation is missing required comparison dimensions")

    if hard_blocked:
        status = ComparisonEligibilityStatus.NOT_ELIGIBLE
    elif required <= set(comparable_dimensions):
        status = ComparisonEligibilityStatus.ELIGIBLE
        reasons.append("all required comparison dimensions are structurally compatible")
    elif len(comparable_required) >= _MINIMUM_PARTIAL_OVERLAP:
        status = ComparisonEligibilityStatus.PARTIALLY_ELIGIBLE
        reasons.append(
            "sufficient required mechanic overlap exists for a bounded partial comparison"
        )
        if blocked_required:
            reasons.append(
                "one or more required dimensions must be excluded from comparison"
            )
    else:
        status = ComparisonEligibilityStatus.NOT_ELIGIBLE
        reasons.append(
            "insufficient required mechanic overlap for a meaningful comparison"
        )

    return ComparisonEligibilityResult(
        status=status,
        as_of=request.as_of,
        left_implementation_id=left.implementation_id,
        right_implementation_id=right.implementation_id,
        concept_id=concept_id,
        comparable_dimensions=comparable_dimensions,
        blocked_dimensions=blocked_dimensions,
        left_only_dimensions=left_only_dimensions,
        right_only_dimensions=right_only_dimensions,
        missing_required_left=missing_required_left,
        missing_required_right=missing_required_right,
        reasons=tuple(reasons),
    )


__all__ = [
    "ComparisonEligibilityError",
    "ComparisonEligibilityRequest",
    "ComparisonEligibilityResult",
    "ComparisonEligibilityStatus",
    "REQUIRED_COMPARISON_DIMENSIONS",
    "evaluate_comparison_eligibility",
]
