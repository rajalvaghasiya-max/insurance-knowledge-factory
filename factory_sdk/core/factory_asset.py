"""
PolicyScna Factory SDK v1.2 — Factory Asset

Base asset contract for all manufactured assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from .factory_lineage import FactoryLineage
from .factory_metadata import FactoryMetadata


class AssetStatus(str, Enum):
    DRAFT = "draft"
    CERTIFIED = "certified"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class AssetPersistence(str, Enum):
    IMMUTABLE = "immutable"
    VERSIONED = "versioned"
    CACHE = "cache"
    TEMPORARY = "temporary"


class AssetTrustBasis(str, Enum):
    EVIDENCE_BACKED = "evidence_backed"
    DERIVED_FROM_APPROVED_INPUTS = "derived_from_approved_inputs"
    ILLUSTRATIVE = "illustrative"
    UNVERIFIED = "unverified"
    INVALID_FOR_USE = "invalid_for_use"


class RuntimeReadiness(str, Enum):
    STANDALONE = "standalone"
    RUNTIME_DEPENDENT = "runtime_dependent"
    BLOCKED = "blocked"


class AssetDisposition(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class FactoryAsset:
    asset_id: str
    asset_type: str
    schema_version: str
    status: AssetStatus
    metadata: FactoryMetadata
    lineage: FactoryLineage
    payload: Dict[str, Any] = field(default_factory=dict)
    quality: Dict[str, Any] = field(default_factory=dict)
    certification: Dict[str, Any] = field(default_factory=dict)
    persistence: AssetPersistence = AssetPersistence.VERSIONED
    trust_basis: AssetTrustBasis = AssetTrustBasis.UNVERIFIED
    runtime_readiness: RuntimeReadiness = RuntimeReadiness.STANDALONE
    disposition: AssetDisposition = AssetDisposition.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "schema_version": self.schema_version,
            "status": self.status.value,
            "persistence": self.persistence.value,
            "trust_basis": self.trust_basis.value,
            "runtime_readiness": self.runtime_readiness.value,
            "disposition": self.disposition.value,
            "metadata": self.metadata.to_dict(),
            "lineage": self.lineage.to_dict(),
            "payload": self.payload,
            "quality": self.quality,
            "certification": self.certification,
        }

    @classmethod
    def wrap_payload(
        cls,
        *,
        asset_id: str,
        asset_type: str,
        schema_version: str,
        metadata: FactoryMetadata,
        lineage: FactoryLineage,
        payload: Dict[str, Any],
        status: AssetStatus = AssetStatus.DRAFT,
        quality: Optional[Dict[str, Any]] = None,
        certification: Optional[Dict[str, Any]] = None,
        persistence: AssetPersistence = AssetPersistence.VERSIONED,
        trust_basis: AssetTrustBasis = AssetTrustBasis.UNVERIFIED,
        runtime_readiness: RuntimeReadiness = RuntimeReadiness.STANDALONE,
        disposition: AssetDisposition = AssetDisposition.ACTIVE,
    ) -> "FactoryAsset":
        return cls(
            asset_id=asset_id,
            asset_type=asset_type,
            schema_version=schema_version,
            status=status,
            metadata=metadata,
            lineage=lineage,
            payload=payload,
            quality=quality or {},
            certification=certification or {},
            persistence=persistence,
            trust_basis=trust_basis,
            runtime_readiness=runtime_readiness,
            disposition=disposition,
        )