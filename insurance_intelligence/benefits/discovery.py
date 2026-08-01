"""Governed benefit discovery for MO-025E.

Discovery returns active, approved, published implementations for one canonical
benefit concept as of a requested date. It does not judge comparability, rank,
recommend, decide entitlement, or generate customer answers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from insurance_intelligence.benefits.contracts import ProductBenefitImplementation
from insurance_intelligence.benefits.registry import registered_benefit_implementations


class BenefitDiscoveryError(ValueError):
    """Raised when a discovery request is structurally invalid."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenefitDiscoveryError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class BenefitDiscoveryRequest:
    concept_id: str
    as_of: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _required_text(self.concept_id, "concept_id"))
        if not isinstance(self.as_of, date):
            raise BenefitDiscoveryError("as_of must be a date")


@dataclass(frozen=True)
class BenefitDiscoveryResult:
    concept_id: str
    as_of: date
    implementations: tuple[ProductBenefitImplementation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _required_text(self.concept_id, "concept_id"))
        if not isinstance(self.as_of, date):
            raise BenefitDiscoveryError("as_of must be a date")
        if not isinstance(self.implementations, tuple):
            raise BenefitDiscoveryError("implementations must be a tuple")
        if not all(isinstance(item, ProductBenefitImplementation) for item in self.implementations):
            raise BenefitDiscoveryError(
                "implementations must contain ProductBenefitImplementation values"
            )
        if any(item.concept_id != self.concept_id for item in self.implementations):
            raise BenefitDiscoveryError("all implementations must match result concept_id")

    @property
    def is_empty(self) -> bool:
        return not self.implementations

    @property
    def count(self) -> int:
        return len(self.implementations)


def discover_benefits(
    request: BenefitDiscoveryRequest,
    *,
    registry: tuple[ProductBenefitImplementation, ...] | None = None,
) -> BenefitDiscoveryResult:
    """Discover governed implementations matching the concept and effective date."""

    if not isinstance(request, BenefitDiscoveryRequest):
        raise BenefitDiscoveryError("request must be a BenefitDiscoveryRequest")

    candidates = registered_benefit_implementations() if registry is None else registry
    if not isinstance(candidates, tuple):
        raise BenefitDiscoveryError("registry must be a tuple")
    if not all(isinstance(item, ProductBenefitImplementation) for item in candidates):
        raise BenefitDiscoveryError(
            "registry must contain ProductBenefitImplementation values"
        )

    matches = tuple(
        sorted(
            (
                item
                for item in candidates
                if item.concept_id == request.concept_id
                and item.is_governed_for_use
                and item.is_active(request.as_of)
            ),
            key=lambda item: (
                item.insurer_id,
                item.product_id,
                item.product_variant_id,
                item.implementation_id,
            ),
        )
    )

    return BenefitDiscoveryResult(
        concept_id=request.concept_id,
        as_of=request.as_of,
        implementations=matches,
    )


__all__ = [
    "BenefitDiscoveryError",
    "BenefitDiscoveryRequest",
    "BenefitDiscoveryResult",
    "discover_benefits",
]
