"""Typed product-level semantics for evidence-backed co-payment rate matrices.

A matrix preserves documented rate cells without manufacturing a customer-specific
scalar.  Resolution of one applicable percentage requires separately governed
policy / claim context identifying the relevant matrix selectors.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CopaymentRateMatrixError(ValueError):
    """Raised when a co-payment matrix contract is incomplete or unsafe."""


class CopaymentCalculationBasis(str, Enum):
    ADMISSIBLE_CLAIM_AMOUNT = "ADMISSIBLE_CLAIM_AMOUNT"
    ENTIRE_CLAIM = "ENTIRE_CLAIM"


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CopaymentRateMatrixError(f"{label} must be non-empty text")
    return value.strip()


def _text_tuple(value: tuple[str, ...], label: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise CopaymentRateMatrixError(f"{label} must be a tuple")
    cleaned = tuple(_text(item, f"{label}[]") for item in value)
    if not cleaned:
        raise CopaymentRateMatrixError(f"{label} must not be empty")
    if len(cleaned) != len(set(cleaned)):
        raise CopaymentRateMatrixError(f"{label} must not contain duplicates")
    return cleaned


@dataclass(frozen=True)
class CopaymentRateMatrixCell:
    plan_variant: str
    claimed_category: str
    percentage: int | float

    def __post_init__(self) -> None:
        object.__setattr__(self, "plan_variant", _text(self.plan_variant, "plan_variant"))
        object.__setattr__(self, "claimed_category", _text(self.claimed_category, "claimed_category"))
        if isinstance(self.percentage, bool) or not isinstance(self.percentage, (int, float)):
            raise CopaymentRateMatrixError("percentage must be numeric")
        if not 0 <= float(self.percentage) <= 100:
            raise CopaymentRateMatrixError("percentage must be between 0 and 100")


@dataclass(frozen=True)
class CopaymentRateMatrixMechanic:
    cells: tuple[CopaymentRateMatrixCell, ...]
    trigger_condition: str
    applicability_scope: str
    calculation_basis: CopaymentCalculationBasis
    evidence_reference_ids: tuple[str, ...]
    instance_resolution_dependency: str
    semantic_variant: str = "ROOM_CATEGORY_RATE_MATRIX"
    matrix_dimensions: tuple[str, ...] = ("PLAN_VARIANT", "CLAIMED_ROOM_CATEGORY")
    instance_resolution_required: bool = True
    unlisted_combination_outcome: str = "UNRESOLVED"

    def __post_init__(self) -> None:
        if not isinstance(self.cells, tuple) or not self.cells:
            raise CopaymentRateMatrixError("cells must be a non-empty tuple")
        if not all(isinstance(cell, CopaymentRateMatrixCell) for cell in self.cells):
            raise CopaymentRateMatrixError("cells must contain CopaymentRateMatrixCell values")
        identities = tuple((cell.plan_variant, cell.claimed_category) for cell in self.cells)
        if len(identities) != len(set(identities)):
            raise CopaymentRateMatrixError("matrix cells must be unique by plan_variant + claimed_category")
        object.__setattr__(self, "trigger_condition", _text(self.trigger_condition, "trigger_condition"))
        object.__setattr__(self, "applicability_scope", _text(self.applicability_scope, "applicability_scope"))
        if not isinstance(self.calculation_basis, CopaymentCalculationBasis):
            raise CopaymentRateMatrixError("calculation_basis must be a CopaymentCalculationBasis")
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
        object.__setattr__(self, "matrix_dimensions", _text_tuple(self.matrix_dimensions, "matrix_dimensions"))
        if self.semantic_variant != "ROOM_CATEGORY_RATE_MATRIX":
            raise CopaymentRateMatrixError("semantic_variant must remain ROOM_CATEGORY_RATE_MATRIX")
        if self.matrix_dimensions != ("PLAN_VARIANT", "CLAIMED_ROOM_CATEGORY"):
            raise CopaymentRateMatrixError(
                "ROOM_CATEGORY_RATE_MATRIX dimensions must be PLAN_VARIANT + CLAIMED_ROOM_CATEGORY"
            )
        if self.instance_resolution_required is not True:
            raise CopaymentRateMatrixError("rate-matrix mechanics must require instance resolution")
        if self.unlisted_combination_outcome != "UNRESOLVED":
            raise CopaymentRateMatrixError("unlisted matrix combinations must remain UNRESOLVED")


__all__ = [
    "CopaymentCalculationBasis",
    "CopaymentRateMatrixCell",
    "CopaymentRateMatrixError",
    "CopaymentRateMatrixMechanic",
]
