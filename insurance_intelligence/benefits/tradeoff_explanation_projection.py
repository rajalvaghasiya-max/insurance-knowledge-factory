"""Education-first comparison explanation projection for MO-026H.

This module converts a governed cross-product trade-off comparison into a
structured presentation payload. It preserves local strengths, restrictions,
protection-floor warnings, unresolved dimensions, and source limitations while
explicitly refusing to create an overall winner or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.tradeoff_comparison import (
    DimensionTradeoff,
    DimensionTradeoffStatus,
    GovernedProductTradeoffComparison,
)


class TradeoffExplanationProjectionError(ValueError):
    """Raised when an explanation projection violates a governance invariant."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeoffExplanationProjectionError(f"{field_name} must be non-empty text")
    return value.strip()


class TradeoffExplanationProjectionStatus(str, Enum):
    READY = "READY"
    READY_WITH_UNRESOLVED_DIMENSIONS = "READY_WITH_UNRESOLVED_DIMENSIONS"


@dataclass(frozen=True)
class TradeoffExplanationItem:
    dimension_id: str
    statement: str
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension_id", _required_text(self.dimension_id, "dimension_id"))
        object.__setattr__(self, "statement", _required_text(self.statement, "statement"))
        if not isinstance(self.limitations, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.limitations
        ):
            raise TradeoffExplanationProjectionError(
                "limitations must contain non-empty text values"
            )


@dataclass(frozen=True)
class GovernedTradeoffExplanationProjection:
    projection_id: str
    comparison_id: str
    left_product_reference: str
    right_product_reference: str
    status: TradeoffExplanationProjectionStatus
    left_strengths: tuple[TradeoffExplanationItem, ...]
    right_strengths: tuple[TradeoffExplanationItem, ...]
    shared_dimensions: tuple[TradeoffExplanationItem, ...]
    protection_floor_warnings: tuple[TradeoffExplanationItem, ...]
    unresolved_dimensions: tuple[TradeoffExplanationItem, ...]
    decision_boundary: str
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "projection_id",
            "comparison_id",
            "left_product_reference",
            "right_product_reference",
            "decision_boundary",
            "contract_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if not isinstance(self.status, TradeoffExplanationProjectionStatus):
            raise TradeoffExplanationProjectionError(
                "status must be a TradeoffExplanationProjectionStatus"
            )
        for field_name in (
            "left_strengths",
            "right_strengths",
            "shared_dimensions",
            "protection_floor_warnings",
            "unresolved_dimensions",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or not all(
                type(item) is TradeoffExplanationItem for item in values
            ):
                raise TradeoffExplanationProjectionError(
                    f"{field_name} must contain exact TradeoffExplanationItem values"
                )
        forbidden = ("winner", "best product", "recommended product", "overall score")
        boundary_lower = self.decision_boundary.lower()
        if "no overall winner" not in boundary_lower:
            raise TradeoffExplanationProjectionError(
                "decision_boundary must explicitly state that there is no overall winner"
            )
        if any(term in boundary_lower for term in forbidden if term != "winner"):
            raise TradeoffExplanationProjectionError(
                "decision_boundary must not create an overall product verdict"
            )


def _item(tradeoff: DimensionTradeoff) -> TradeoffExplanationItem:
    return TradeoffExplanationItem(
        dimension_id=tradeoff.dimension_id,
        statement=tradeoff.explanation,
        limitations=tradeoff.limitations,
    )


def project_tradeoff_explanation(
    comparison: GovernedProductTradeoffComparison,
) -> GovernedTradeoffExplanationProjection:
    """Create a deterministic education-first presentation payload."""

    if type(comparison) is not GovernedProductTradeoffComparison:
        raise TradeoffExplanationProjectionError(
            "comparison must be the exact GovernedProductTradeoffComparison type"
        )

    left_strengths = tuple(
        _item(item)
        for item in comparison.dimensions
        if item.status is DimensionTradeoffStatus.LEFT_STRONGER
    )
    right_strengths = tuple(
        _item(item)
        for item in comparison.dimensions
        if item.status is DimensionTradeoffStatus.RIGHT_STRONGER
    )
    shared = tuple(
        _item(item)
        for item in comparison.dimensions
        if item.status is DimensionTradeoffStatus.SHARED
    )
    protection_floor = tuple(_item(item) for item in comparison.protection_floor_warnings)
    unresolved = tuple(_item(item) for item in comparison.unresolved_dimensions)
    status = (
        TradeoffExplanationProjectionStatus.READY_WITH_UNRESOLVED_DIMENSIONS
        if unresolved
        else TradeoffExplanationProjectionStatus.READY
    )

    return GovernedTradeoffExplanationProjection(
        projection_id=f"tradeoff_explanation:{comparison.comparison_id}",
        comparison_id=comparison.comparison_id,
        left_product_reference=comparison.left_product_reference,
        right_product_reference=comparison.right_product_reference,
        status=status,
        left_strengths=left_strengths,
        right_strengths=right_strengths,
        shared_dimensions=shared,
        protection_floor_warnings=protection_floor,
        unresolved_dimensions=unresolved,
        decision_boundary=(
            "This comparison explains governed strengths, restrictions, trade-offs, and unknowns. "
            "There is no overall winner at this stage; the user decides which trade-offs matter. "
            "A personalized recommendation requires an explicit request and sufficient customer priorities/context."
        ),
    )


__all__ = [
    "GovernedTradeoffExplanationProjection",
    "TradeoffExplanationItem",
    "TradeoffExplanationProjectionError",
    "TradeoffExplanationProjectionStatus",
    "project_tradeoff_explanation",
]
