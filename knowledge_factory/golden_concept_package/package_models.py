from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


@dataclass
class AssetRecord:
    asset_type: str
    status: str
    path: Optional[str] = None
    certification_status: str = "UNKNOWN"
    asset_id: Optional[str] = None
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageAnalysis:
    knowledge_asset: str
    understanding_asset: str
    mental_model_asset: str
    financial_outcome_asset: str
    advisor_intelligence_asset: str
    decision_intelligence_asset: str
    overall: str


@dataclass
class PackageCertification:
    certification_id: str
    package_id: str
    concept_id: str
    status: str
    score: int
    checks: Dict[str, Any]
    issues: List[str]
    created_at: str


@dataclass
class GoldenConceptPackage:
    package_id: str
    concept_id: str
    concept_name: str
    version: str
    created_at: str
    asset_inventory: Dict[str, AssetRecord]
    cross_asset_consistency: Dict[str, Any]
    coverage_analysis: CoverageAnalysis
    gap_analysis: Dict[str, Any]
    maturity_level: str
    package_certification: PackageCertification
    factory_signature: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
