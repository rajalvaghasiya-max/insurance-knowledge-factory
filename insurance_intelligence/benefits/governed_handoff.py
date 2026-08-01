"""Fail-closed handoff contract for future governed ranking consumers.

Only the deterministic comparison explanation projection produced by the active
insurance_intelligence pipeline may cross this boundary. Historical generated
outputs, dictionaries, files, recommendation objects, and arbitrary legacy
objects are intentionally rejected.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.benefits.explanation_projection import (
    ExplanationProjectionStatus,
    GovernedComparisonExplanationProjection,
)


class GovernedHandoffError(ValueError):
    """Raised when an ungoverned or unusable payload reaches the handoff."""


@dataclass(frozen=True)
class GovernedComparisonHandoff:
    projection: GovernedComparisonExplanationProjection
    contract_version: str = "1.0"

    def __post_init__(self) -> None:
        if type(self.projection) is not GovernedComparisonExplanationProjection:
            raise GovernedHandoffError(
                "projection must be the exact governed comparison explanation projection type"
            )
        if self.projection.status not in {
            ExplanationProjectionStatus.READY,
            ExplanationProjectionStatus.READY_WITH_SOURCE_LIMITATIONS,
        }:
            raise GovernedHandoffError("blocked comparison projections cannot enter ranking")
        if not isinstance(self.contract_version, str) or not self.contract_version.strip():
            raise GovernedHandoffError("contract_version must be non-empty text")
        object.__setattr__(self, "contract_version", self.contract_version.strip())

    @property
    def concept_id(self) -> str:
        return self.projection.concept_id

    @property
    def as_of(self):
        return self.projection.as_of


def build_governed_comparison_handoff(
    projection: GovernedComparisonExplanationProjection,
) -> GovernedComparisonHandoff:
    """Validate and freeze the sole admissible pre-ranking comparison payload."""

    return GovernedComparisonHandoff(projection=projection)


__all__ = [
    "GovernedComparisonHandoff",
    "GovernedHandoffError",
    "build_governed_comparison_handoff",
]
