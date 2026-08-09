"""Deterministic presentation projection for governed benefit comparisons.

This module converts a governed comparison outcome into a structured explanation
payload. It does not generate free-form prose, rank products, recommend a product,
infer suitability or entitlement, or assess claims.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from insurance_intelligence.benefits.comparison import (
    ComparisonDimension,
    ComparisonDimensionStatus,
    ComparisonSideIdentity,
)
from insurance_intelligence.benefits.orchestration import (
    ComparisonOrchestrationStatus,
    GovernedComparisonOutcome,
)


class ComparisonExplanationProjectionError(ValueError):
    """Raised when an explanation projection cannot be built safely."""


class ExplanationProjectionStatus(str, Enum):
    READY = "READY"
    READY_WITH_SOURCE_LIMITATIONS = "READY_WITH_SOURCE_LIMITATIONS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ExplanationSide:
    implementation_id: str
    insurer_id: str | None
    product_id: str | None
    product_variant_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.implementation_id, str) or not self.implementation_id.strip():
            raise ComparisonExplanationProjectionError(
                "implementation_id must be non-empty text"
            )
        object.__setattr__(self, "implementation_id", self.implementation_id.strip())
        for field_name in ("insurer_id", "product_id", "product_variant_id"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ComparisonExplanationProjectionError(
                    f"{field_name} must be non-empty text or None"
                )
            if value is not None:
                object.__setattr__(self, field_name, value.strip())


@dataclass(frozen=True)
class ExplanationMechanic:
    dimension_id: str
    left_value: object | None
    right_value: object | None
    unit: str | None
    left_source_dimension_ids: tuple[str, ...]
    right_source_dimension_ids: tuple[str, ...]
    left_evidence_reference_ids: tuple[str, ...]
    right_evidence_reference_ids: tuple[str, ...]
    note: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dimension_id, str) or not self.dimension_id.strip():
            raise ComparisonExplanationProjectionError(
                "dimension_id must be non-empty text"
            )
        object.__setattr__(self, "dimension_id", self.dimension_id.strip())
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise ComparisonExplanationProjectionError("unit must be non-empty text or None")
        if self.note is not None and (not isinstance(self.note, str) or not self.note.strip()):
            raise ComparisonExplanationProjectionError("note must be non-empty text or None")
        for field_name in (
            "left_source_dimension_ids",
            "right_source_dimension_ids",
            "left_evidence_reference_ids",
            "right_evidence_reference_ids",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple):
                raise ComparisonExplanationProjectionError(f"{field_name} must be a tuple")


@dataclass(frozen=True)
class GovernedComparisonExplanationProjection:
    status: ExplanationProjectionStatus
    orchestration_status: ComparisonOrchestrationStatus
    concept_id: str
    as_of: object
    left: ExplanationSide
    right: ExplanationSide
    shared_mechanics: tuple[ExplanationMechanic, ...]
    different_mechanics: tuple[ExplanationMechanic, ...]
    left_only_mechanics: tuple[ExplanationMechanic, ...]
    right_only_mechanics: tuple[ExplanationMechanic, ...]
    blocked_mechanics: tuple[ExplanationMechanic, ...]
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, ExplanationProjectionStatus):
            raise ComparisonExplanationProjectionError(
                "status must be an ExplanationProjectionStatus"
            )
        if not isinstance(self.orchestration_status, ComparisonOrchestrationStatus):
            raise ComparisonExplanationProjectionError(
                "orchestration_status must be a ComparisonOrchestrationStatus"
            )
        if not isinstance(self.concept_id, str) or not self.concept_id.strip():
            raise ComparisonExplanationProjectionError("concept_id must be non-empty text")
        if not isinstance(self.left, ExplanationSide) or not isinstance(self.right, ExplanationSide):
            raise ComparisonExplanationProjectionError("left and right must be ExplanationSide values")
        for field_name in (
            "shared_mechanics",
            "different_mechanics",
            "left_only_mechanics",
            "right_only_mechanics",
            "blocked_mechanics",
        ):
            values = getattr(self, field_name)
            if not isinstance(values, tuple) or not all(
                isinstance(value, ExplanationMechanic) for value in values
            ):
                raise ComparisonExplanationProjectionError(
                    f"{field_name} must contain ExplanationMechanic values"
                )
            ids = tuple(value.dimension_id for value in values)
            if ids != tuple(sorted(ids)):
                raise ComparisonExplanationProjectionError(
                    f"{field_name} must be deterministically ordered"
                )
        if not isinstance(self.reasons, tuple) or not self.reasons:
            raise ComparisonExplanationProjectionError("reasons must be a non-empty tuple")
        if not isinstance(self.limitations, tuple) or not self.limitations:
            raise ComparisonExplanationProjectionError("limitations must be a non-empty tuple")
        has_mechanics = any(
            (
                self.shared_mechanics,
                self.different_mechanics,
                self.left_only_mechanics,
                self.right_only_mechanics,
                self.blocked_mechanics,
            )
        )
        if self.status is ExplanationProjectionStatus.BLOCKED and has_mechanics:
            raise ComparisonExplanationProjectionError(
                "blocked projections cannot contain comparison mechanics"
            )

    @property
    def is_ready(self) -> bool:
        return self.status in {
            ExplanationProjectionStatus.READY,
            ExplanationProjectionStatus.READY_WITH_SOURCE_LIMITATIONS,
        }


_PROJECTION_LIMITATIONS = (
    "This payload is a deterministic projection of governed comparison data, not generated advice.",
    "Shared and different mechanics are factual classifications and do not indicate product superiority.",
    "One-sided mechanics show scope differences only and are not ranking signals.",
    "Customer circumstances, policy schedules, endorsements, claim facts, and suitability remain outside this payload.",
)


def _side(identity: ComparisonSideIdentity | None, implementation_id: str) -> ExplanationSide:
    if identity is None:
        return ExplanationSide(
            implementation_id=implementation_id,
            insurer_id=None,
            product_id=None,
            product_variant_id=None,
        )
    return ExplanationSide(
        implementation_id=identity.implementation_id,
        insurer_id=identity.insurer_id,
        product_id=identity.product_id,
        product_variant_id=identity.product_variant_id,
    )


def _mechanic(item: ComparisonDimension) -> ExplanationMechanic:
    return ExplanationMechanic(
        dimension_id=item.dimension_id,
        left_value=item.left_value,
        right_value=item.right_value,
        unit=item.unit,
        left_source_dimension_ids=item.left_source_dimension_ids,
        right_source_dimension_ids=item.right_source_dimension_ids,
        left_evidence_reference_ids=item.left_evidence_reference_ids,
        right_evidence_reference_ids=item.right_evidence_reference_ids,
        note=item.reason,
    )


def _project_status(
    status: ComparisonOrchestrationStatus,
) -> ExplanationProjectionStatus:
    if status is ComparisonOrchestrationStatus.BLOCKED:
        return ExplanationProjectionStatus.BLOCKED
    if status is ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY:
        return ExplanationProjectionStatus.READY_WITH_SOURCE_LIMITATIONS
    return ExplanationProjectionStatus.READY


def project_comparison_explanation(
    outcome: GovernedComparisonOutcome,
) -> GovernedComparisonExplanationProjection:
    """Project a governed comparison outcome into a presentation-safe payload."""

    if not isinstance(outcome, GovernedComparisonOutcome):
        raise ComparisonExplanationProjectionError(
            "outcome must be a GovernedComparisonOutcome"
        )

    comparison = outcome.comparison
    if outcome.status is ComparisonOrchestrationStatus.BLOCKED:
        if comparison is not None:
            raise ComparisonExplanationProjectionError(
                "blocked orchestration outcomes cannot contain a comparison"
            )
        return GovernedComparisonExplanationProjection(
            status=ExplanationProjectionStatus.BLOCKED,
            orchestration_status=outcome.status,
            concept_id=outcome.request.concept_id,
            as_of=outcome.request.as_of,
            left=_side(None, outcome.request.left_implementation_id),
            right=_side(None, outcome.request.right_implementation_id),
            shared_mechanics=(),
            different_mechanics=(),
            left_only_mechanics=(),
            right_only_mechanics=(),
            blocked_mechanics=(),
            reasons=outcome.reasons,
            limitations=outcome.limitations + _PROJECTION_LIMITATIONS,
        )

    if comparison is None:
        raise ComparisonExplanationProjectionError(
            "non-blocked orchestration outcomes require a comparison"
        )

    by_status = {
        status: tuple(
            sorted(
                (_mechanic(item) for item in comparison.dimensions_with_status(status)),
                key=lambda item: item.dimension_id,
            )
        )
        for status in ComparisonDimensionStatus
    }

    return GovernedComparisonExplanationProjection(
        status=_project_status(outcome.status),
        orchestration_status=outcome.status,
        concept_id=comparison.concept_id,
        as_of=outcome.request.as_of,
        left=_side(comparison.left, outcome.request.left_implementation_id),
        right=_side(comparison.right, outcome.request.right_implementation_id),
        shared_mechanics=by_status[ComparisonDimensionStatus.SHARED],
        different_mechanics=by_status[ComparisonDimensionStatus.DIFFERENT],
        left_only_mechanics=by_status[ComparisonDimensionStatus.LEFT_ONLY],
        right_only_mechanics=by_status[ComparisonDimensionStatus.RIGHT_ONLY],
        blocked_mechanics=by_status[ComparisonDimensionStatus.BLOCKED],
        reasons=outcome.reasons,
        limitations=outcome.limitations + _PROJECTION_LIMITATIONS,
    )


__all__ = [
    "ComparisonExplanationProjectionError",
    "ExplanationMechanic",
    "ExplanationProjectionStatus",
    "ExplanationSide",
    "GovernedComparisonExplanationProjection",
    "project_comparison_explanation",
]
