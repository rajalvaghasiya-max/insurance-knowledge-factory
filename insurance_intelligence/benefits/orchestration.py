"""Governed benefit comparison orchestration for MO-025I.

This application service connects governed discovery, source-record eligibility,
canonical normalization, and factual structured comparison. It returns explicit
outcomes and never ranks, recommends, infers suitability or entitlement, assesses
claims, or generates customer-facing advice.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from insurance_intelligence.benefits.comparison import (
    NormalizedBenefitComparisonResult,
    compare_normalized_benefits,
)
from insurance_intelligence.benefits.contracts import ProductBenefitImplementation
from insurance_intelligence.benefits.discovery import (
    BenefitDiscoveryRequest,
    discover_benefits,
)
from insurance_intelligence.benefits.eligibility import (
    ComparisonEligibilityRequest,
    ComparisonEligibilityResult,
    ComparisonEligibilityStatus,
    evaluate_comparison_eligibility,
)
from insurance_intelligence.benefits.normalization import normalize_for_comparison


class ComparisonOrchestrationError(ValueError):
    """Raised when an orchestration request is structurally invalid."""


class ComparisonOrchestrationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PARTIAL_SOURCE_ELIGIBILITY = "PARTIAL_SOURCE_ELIGIBILITY"
    BLOCKED = "BLOCKED"


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparisonOrchestrationError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class GovernedComparisonRequest:
    concept_id: str
    left_implementation_id: str
    right_implementation_id: str
    as_of: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _required_text(self.concept_id, "concept_id"))
        object.__setattr__(
            self,
            "left_implementation_id",
            _required_text(self.left_implementation_id, "left_implementation_id"),
        )
        object.__setattr__(
            self,
            "right_implementation_id",
            _required_text(self.right_implementation_id, "right_implementation_id"),
        )
        if self.left_implementation_id == self.right_implementation_id:
            raise ComparisonOrchestrationError(
                "left and right implementation identities must differ"
            )
        if not isinstance(self.as_of, date):
            raise ComparisonOrchestrationError("as_of must be a date")


@dataclass(frozen=True)
class GovernedComparisonOutcome:
    status: ComparisonOrchestrationStatus
    request: GovernedComparisonRequest
    discovered_implementation_ids: tuple[str, ...]
    eligibility: ComparisonEligibilityResult | None
    comparison: NormalizedBenefitComparisonResult | None
    reasons: tuple[str, ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, ComparisonOrchestrationStatus):
            raise ComparisonOrchestrationError(
                "status must be a ComparisonOrchestrationStatus"
            )
        if not isinstance(self.request, GovernedComparisonRequest):
            raise ComparisonOrchestrationError(
                "request must be a GovernedComparisonRequest"
            )
        if not isinstance(self.discovered_implementation_ids, tuple):
            raise ComparisonOrchestrationError(
                "discovered_implementation_ids must be a tuple"
            )
        if tuple(sorted(self.discovered_implementation_ids)) != self.discovered_implementation_ids:
            raise ComparisonOrchestrationError(
                "discovered implementation identities must be deterministically ordered"
            )
        if not isinstance(self.reasons, tuple) or not self.reasons:
            raise ComparisonOrchestrationError("reasons must be a non-empty tuple")
        if not isinstance(self.limitations, tuple) or not self.limitations:
            raise ComparisonOrchestrationError("limitations must be a non-empty tuple")
        if self.status is ComparisonOrchestrationStatus.BLOCKED and self.comparison is not None:
            raise ComparisonOrchestrationError("blocked outcomes cannot contain a comparison")
        if self.status is not ComparisonOrchestrationStatus.BLOCKED and self.comparison is None:
            raise ComparisonOrchestrationError(
                "non-blocked outcomes must contain a comparison"
            )

    @property
    def is_completed(self) -> bool:
        return self.status is ComparisonOrchestrationStatus.COMPLETED

    @property
    def is_blocked(self) -> bool:
        return self.status is ComparisonOrchestrationStatus.BLOCKED


_DEFAULT_LIMITATIONS = (
    "Only active, approved, published implementations discovered for the requested concept and date are eligible for orchestration.",
    "A completed factual comparison is not a ranking, recommendation, suitability conclusion, entitlement decision, or claim assessment.",
    "Source-record partial eligibility is preserved even when canonical normalization permits a complete factual projection comparison.",
)


def _resolve_requested_implementation(
    implementation_id: str,
    implementations: tuple[ProductBenefitImplementation, ...],
) -> ProductBenefitImplementation | None:
    matches = tuple(
        item for item in implementations if item.implementation_id == implementation_id
    )
    if len(matches) > 1:
        raise ComparisonOrchestrationError(
            f"duplicate discovered implementation identity: {implementation_id}"
        )
    return matches[0] if matches else None


def orchestrate_governed_comparison(
    request: GovernedComparisonRequest,
    *,
    registry: tuple[ProductBenefitImplementation, ...] | None = None,
) -> GovernedComparisonOutcome:
    """Run the governed comparison pipeline for two requested implementations."""

    if not isinstance(request, GovernedComparisonRequest):
        raise ComparisonOrchestrationError(
            "request must be a GovernedComparisonRequest"
        )

    discovery = discover_benefits(
        BenefitDiscoveryRequest(concept_id=request.concept_id, as_of=request.as_of),
        registry=registry,
    )
    discovered_ids = tuple(
        sorted(item.implementation_id for item in discovery.implementations)
    )
    left = _resolve_requested_implementation(
        request.left_implementation_id, discovery.implementations
    )
    right = _resolve_requested_implementation(
        request.right_implementation_id, discovery.implementations
    )

    missing: list[str] = []
    if left is None:
        missing.append(
            "left implementation was not discovered as active, approved, and published for the requested concept and date"
        )
    if right is None:
        missing.append(
            "right implementation was not discovered as active, approved, and published for the requested concept and date"
        )
    if missing:
        return GovernedComparisonOutcome(
            status=ComparisonOrchestrationStatus.BLOCKED,
            request=request,
            discovered_implementation_ids=discovered_ids,
            eligibility=None,
            comparison=None,
            reasons=tuple(missing),
            limitations=_DEFAULT_LIMITATIONS,
        )

    eligibility = evaluate_comparison_eligibility(
        ComparisonEligibilityRequest(left=left, right=right, as_of=request.as_of)
    )
    if eligibility.status is ComparisonEligibilityStatus.NOT_ELIGIBLE:
        return GovernedComparisonOutcome(
            status=ComparisonOrchestrationStatus.BLOCKED,
            request=request,
            discovered_implementation_ids=discovered_ids,
            eligibility=eligibility,
            comparison=None,
            reasons=eligibility.reasons,
            limitations=_DEFAULT_LIMITATIONS,
        )

    left_projection = normalize_for_comparison(left)
    right_projection = normalize_for_comparison(right)
    comparison = compare_normalized_benefits(left_projection, right_projection)

    if comparison.blocked_dimensions:
        return GovernedComparisonOutcome(
            status=ComparisonOrchestrationStatus.BLOCKED,
            request=request,
            discovered_implementation_ids=discovered_ids,
            eligibility=eligibility,
            comparison=None,
            reasons=(
                "canonical comparison contains one or more blocked dimensions",
            ),
            limitations=_DEFAULT_LIMITATIONS,
        )

    status = (
        ComparisonOrchestrationStatus.COMPLETED
        if eligibility.status is ComparisonEligibilityStatus.ELIGIBLE
        else ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY
    )
    reasons = (
        "governed comparison completed after discovery, eligibility, normalization, and factual comparison",
    )
    if status is ComparisonOrchestrationStatus.PARTIAL_SOURCE_ELIGIBILITY:
        reasons += (
            "source-record eligibility was partial, while canonical normalization resolved representation differences for factual comparison",
        )

    return GovernedComparisonOutcome(
        status=status,
        request=request,
        discovered_implementation_ids=discovered_ids,
        eligibility=eligibility,
        comparison=comparison,
        reasons=reasons,
        limitations=_DEFAULT_LIMITATIONS + comparison.limitations,
    )


__all__ = [
    "ComparisonOrchestrationError",
    "ComparisonOrchestrationStatus",
    "GovernedComparisonOutcome",
    "GovernedComparisonRequest",
    "orchestrate_governed_comparison",
]
