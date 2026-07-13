"""Contracts for evidence-backed Product Identity Resolution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class IdentityResolutionStatus(StrEnum):
    VERIFIED = "verified"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class ProductIdentityDecision:
    """A decision about an already product-scoped intelligence asset.

    A decision is intentionally separate from a Product Master record. Product
    Master remains discovery/consolidation output; this contract decides whether
    a UIN-backed identity can be trusted as a canonical product identity.
    """

    entity_id: str
    insurer_id: str
    product_slug: str
    product_name: str | None
    uin: str | None
    status: IdentityResolutionStatus
    resolution_method: str | None
    reasons: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    source_intelligence_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "insurer_id": self.insurer_id,
            "product_slug": self.product_slug,
            "product_name": self.product_name,
            "uin": self.uin,
            "resolution_status": self.status.value,
            "resolution_method": self.resolution_method,
            "reasons": list(self.reasons),
            "evidence": [dict(item) for item in self.evidence],
            "source_intelligence_file": self.source_intelligence_file,
        }
