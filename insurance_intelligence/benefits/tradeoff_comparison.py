"""Education-first cross-product trade-off comparison for MO-026G.

This layer compares two already-governed product assessment profiles one dimension
at a time. A local dimension may be described as stronger, weaker, shared, or
unresolved. The contract deliberately has no aggregate score, rank, winner,
weighting, suitability conclusion, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.assessment_contracts import (
    AssessmentBand,
    AssessmentStatus,
    BenefitAssessment,
    DecisionRole,
)
from insurance_intelligence.benefits.product_assessment_profile import (
    GovernedProductBenefitAssessmentProfile,
    ProductAssessmentEntry,
)


class TradeoffComparisonError(ValueError):
    """Raised when governed profiles cannot be compared safely."""


class DimensionTradeoffStatus(str, Enum):
    SHARED = "SHARED"
    LEFT_STRONGER = "LEFT_STRONGER"
    RIGHT_STRONGER = "RIGHT_STRONGER"
    UNRESOLVED = "UNRESOLVED"
    LEFT_ONLY = "LEFT_ONLY"
    RIGHT_ONLY = "RIGHT_ONLY"
    NOT_COMPARABLE = "NOT_COMPARABLE"


_BAND_ORDER = {
    AssessmentBand.VERY_RESTRICTIVE: 0,
    AssessmentBand.RESTRICTIVE: 1,
    AssessmentBand.MODERATE: 2,
    AssessmentBand.STRONG: 3,
    AssessmentBand.VERY_STRONG: 4,
}


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TradeoffComparisonError(f"{field_name} must be non-empty text")
    return value.strip()


def _assessment_is_resolved(assessment: BenefitAssessment) -> bool:
    return assessment.status in {
        AssessmentStatus.ASSESSED,
        AssessmentStatus.ASSESSED_WITH_LIMITATIONS,
    }


@dataclass(frozen=True)
class DimensionTradeoff:
    dimension_id: str
    decision_role: DecisionRole
    status: DimensionTradeoffStatus
    left_assessment: BenefitAssessment | None
    right_assessment: BenefitAssessment | None
    explanation: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension_id", _required_text(self.dimension_id, "dimension_id"))
        if not isinstance(self.decision_role, DecisionRole):
            raise TradeoffComparisonError("decision_role must be a DecisionRole")
        if not isinstance(self.status, DimensionTradeoffStatus):
            raise TradeoffComparisonError("status must be a DimensionTradeoffStatus")
        for name in ("left_assessment", "right_assessment"):
            value = getattr(self, name)
            if value is not None and type(value) is not BenefitAssessment:
                raise TradeoffComparisonError(f"{name} must be the exact BenefitAssessment type or None")
            if value is not None and value.dimension_id != self.dimension_id:
                raise TradeoffComparisonError(f"{name} dimension_id must match trade-off dimension")
            if value is not None and value.decision_role is not self.decision_role:
                raise TradeoffComparisonError(f"{name} decision_role must match trade-off decision_role")
        object.__setattr__(self, "explanation", _required_text(self.explanation, "explanation"))
        if not isinstance(self.limitations, tuple) or not all(
            isinstance(item, str) and item.strip() for item in self.limitations
        ):
            raise TradeoffComparisonError("limitations must contain non-empty text values")

    @property
    def is_protection_floor_warning(self) -> bool:
        if self.decision_role is not DecisionRole.PROTECTION_FLOOR:
            return False
        if self.status in {
            DimensionTradeoffStatus.UNRESOLVED,
            DimensionTradeoffStatus.NOT_COMPARABLE,
            DimensionTradeoffStatus.LEFT_ONLY,
            DimensionTradeoffStatus.RIGHT_ONLY,
        }:
            return True
        return any(
            assessment is not None
            and assessment.assessment_band in {
                AssessmentBand.RESTRICTIVE,
                AssessmentBand.VERY_RESTRICTIVE,
            }
            for assessment in (self.left_assessment, self.right_assessment)
        )


@dataclass(frozen=True)
class GovernedProductTradeoffComparison:
    comparison_id: str
    left_product_reference: str
    right_product_reference: str
    dimensions: tuple[DimensionTradeoff, ...]
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        for field_name in (
            "comparison_id",
            "left_product_reference",
            "right_product_reference",
            "contract_version",
        ):
            object.__setattr__(
                self,
                field_name,
                _required_text(getattr(self, field_name), field_name),
            )
        if self.left_product_reference == self.right_product_reference:
            raise TradeoffComparisonError("left and right product references must be different")
        if not isinstance(self.dimensions, tuple) or not self.dimensions:
            raise TradeoffComparisonError("dimensions must be a non-empty tuple")
        if not all(type(item) is DimensionTradeoff for item in self.dimensions):
            raise TradeoffComparisonError("dimensions must contain exact DimensionTradeoff values")
        ids = tuple(item.dimension_id for item in self.dimensions)
        if len(ids) != len(set(ids)):
            raise TradeoffComparisonError("comparison must not contain duplicate dimensions")
        object.__setattr__(
            self,
            "dimensions",
            tuple(sorted(self.dimensions, key=lambda item: item.dimension_id)),
        )

    @property
    def left_stronger_dimensions(self) -> tuple[DimensionTradeoff, ...]:
        return tuple(
            item for item in self.dimensions if item.status is DimensionTradeoffStatus.LEFT_STRONGER
        )

    @property
    def right_stronger_dimensions(self) -> tuple[DimensionTradeoff, ...]:
        return tuple(
            item for item in self.dimensions if item.status is DimensionTradeoffStatus.RIGHT_STRONGER
        )

    @property
    def unresolved_dimensions(self) -> tuple[DimensionTradeoff, ...]:
        return tuple(
            item
            for item in self.dimensions
            if item.status
            in {
                DimensionTradeoffStatus.UNRESOLVED,
                DimensionTradeoffStatus.NOT_COMPARABLE,
                DimensionTradeoffStatus.LEFT_ONLY,
                DimensionTradeoffStatus.RIGHT_ONLY,
            }
        )

    @property
    def protection_floor_warnings(self) -> tuple[DimensionTradeoff, ...]:
        return tuple(item for item in self.dimensions if item.is_protection_floor_warning)


def _entry_map(
    profile: GovernedProductBenefitAssessmentProfile,
) -> dict[str, ProductAssessmentEntry]:
    return {item.assessment.dimension_id: item for item in profile.entries}


def _one_sided_tradeoff(
    *,
    dimension_id: str,
    entry: ProductAssessmentEntry,
    left: bool,
) -> DimensionTradeoff:
    side = "left" if left else "right"
    status = DimensionTradeoffStatus.LEFT_ONLY if left else DimensionTradeoffStatus.RIGHT_ONLY
    return DimensionTradeoff(
        dimension_id=dimension_id,
        decision_role=entry.assessment.decision_role,
        status=status,
        left_assessment=entry.assessment if left else None,
        right_assessment=None if left else entry.assessment,
        explanation=(
            f"Only the {side} product has a governed assessment for this dimension. "
            "Absence on the other side must not be interpreted as superiority or inferiority."
        ),
        limitations=("The dimension is not available on a common governed comparison basis.",),
    )


def _compare_common_dimension(
    left: BenefitAssessment,
    right: BenefitAssessment,
) -> DimensionTradeoff:
    if left.dimension_id != right.dimension_id:
        raise TradeoffComparisonError("common-dimension comparison requires matching dimension ids")
    if left.decision_role is not right.decision_role:
        raise TradeoffComparisonError(
            f"decision-role mismatch for dimension {left.dimension_id!r}"
        )

    dimension_id = left.dimension_id
    role = left.decision_role
    combined_limitations = tuple(dict.fromkeys(left.limitations + right.limitations))

    if not _assessment_is_resolved(left) or not _assessment_is_resolved(right):
        return DimensionTradeoff(
            dimension_id=dimension_id,
            decision_role=role,
            status=DimensionTradeoffStatus.UNRESOLVED,
            left_assessment=left,
            right_assessment=right,
            explanation=(
                "A governed local comparison is unavailable because at least one product has an unresolved "
                "assessment for this dimension."
            ),
            limitations=combined_limitations
            + ("No stronger/weaker conclusion is permitted while either side is unresolved.",),
        )

    if left.assessment_policy_id != right.assessment_policy_id or (
        left.assessment_policy_version != right.assessment_policy_version
    ):
        return DimensionTradeoff(
            dimension_id=dimension_id,
            decision_role=role,
            status=DimensionTradeoffStatus.NOT_COMPARABLE,
            left_assessment=left,
            right_assessment=right,
            explanation=(
                "Both products are assessed, but their assessment-policy identities or versions differ, "
                "so PolicyScna will not compare their qualitative bands directly."
            ),
            limitations=combined_limitations
            + ("A common governed assessment policy is required for direct qualitative comparison.",),
        )

    assert left.assessment_band is not None
    assert right.assessment_band is not None
    left_value = _BAND_ORDER[left.assessment_band]
    right_value = _BAND_ORDER[right.assessment_band]

    if left_value == right_value:
        status = DimensionTradeoffStatus.SHARED
        explanation = (
            f"Both products have the same governed qualitative band ({left.assessment_band.value}) "
            "for this dimension."
        )
    elif left_value > right_value:
        status = DimensionTradeoffStatus.LEFT_STRONGER
        explanation = (
            f"The left product is stronger on this dimension under the common governed assessment policy: "
            f"{left.assessment_band.value} versus {right.assessment_band.value}."
        )
    else:
        status = DimensionTradeoffStatus.RIGHT_STRONGER
        explanation = (
            f"The right product is stronger on this dimension under the common governed assessment policy: "
            f"{right.assessment_band.value} versus {left.assessment_band.value}."
        )

    return DimensionTradeoff(
        dimension_id=dimension_id,
        decision_role=role,
        status=status,
        left_assessment=left,
        right_assessment=right,
        explanation=explanation,
        limitations=combined_limitations,
    )


def compare_product_assessment_profiles(
    *,
    comparison_id: str,
    left: GovernedProductBenefitAssessmentProfile,
    right: GovernedProductBenefitAssessmentProfile,
) -> GovernedProductTradeoffComparison:
    """Compare two governed profiles dimension-by-dimension without an overall verdict."""

    if type(left) is not GovernedProductBenefitAssessmentProfile:
        raise TradeoffComparisonError(
            "left must be the exact GovernedProductBenefitAssessmentProfile type"
        )
    if type(right) is not GovernedProductBenefitAssessmentProfile:
        raise TradeoffComparisonError(
            "right must be the exact GovernedProductBenefitAssessmentProfile type"
        )
    if left.product_reference == right.product_reference:
        raise TradeoffComparisonError("cannot compare a product profile with itself")

    left_map = _entry_map(left)
    right_map = _entry_map(right)
    dimension_ids = tuple(sorted(set(left_map) | set(right_map)))
    tradeoffs: list[DimensionTradeoff] = []
    for dimension_id in dimension_ids:
        left_entry = left_map.get(dimension_id)
        right_entry = right_map.get(dimension_id)
        if left_entry is None:
            assert right_entry is not None
            tradeoffs.append(
                _one_sided_tradeoff(
                    dimension_id=dimension_id,
                    entry=right_entry,
                    left=False,
                )
            )
        elif right_entry is None:
            tradeoffs.append(
                _one_sided_tradeoff(
                    dimension_id=dimension_id,
                    entry=left_entry,
                    left=True,
                )
            )
        else:
            tradeoffs.append(
                _compare_common_dimension(left_entry.assessment, right_entry.assessment)
            )

    return GovernedProductTradeoffComparison(
        comparison_id=comparison_id,
        left_product_reference=left.product_reference,
        right_product_reference=right.product_reference,
        dimensions=tuple(tradeoffs),
    )


__all__ = [
    "DimensionTradeoff",
    "DimensionTradeoffStatus",
    "GovernedProductTradeoffComparison",
    "TradeoffComparisonError",
    "compare_product_assessment_profiles",
]
