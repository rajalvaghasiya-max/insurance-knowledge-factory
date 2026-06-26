"""
PolicyScna Factory SDK v1.0 — Core Models

Purpose:
    Shared contracts for deterministic production lines, manufactured assets,
    manufacturing reports, certification results, and factory events.

Design principles:
    - Law 0: deterministic manufacturing
    - Law 1: evidence preservation
    - one engine -> one asset type
    - reports and certification are first-class outputs
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class CertificationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class AssetPersistence(str, Enum):
    IMMUTABLE = "immutable"
    VERSIONED = "versioned"
    CACHE = "cache"
    TEMPORARY = "temporary"


@dataclass(frozen=True)
class ProductionLineContract:
    engine_name: str
    department: str
    production_line: str
    consumes: str
    manufactures: str
    customer_department: str
    engine_version: str
    rules_version: str
    schema_version: str
    deterministic: bool
    certification_required: bool
    department_boundary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityWarning:
    type: str
    severity: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CertificationResult:
    validation_status: CertificationStatus
    quality_score: float
    gates_passed: List[str] = field(default_factory=list)
    gates_failed: List[str] = field(default_factory=list)
    warnings: List[QualityWarning] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["validation_status"] = self.validation_status.value
        return data


@dataclass
class ManufacturedAssetHeader:
    asset_id: str
    asset_type: str
    schema_version: str
    engine_version: str
    rules_version: str
    factory_version: str
    manufactured_at: str
    manufactured_by: str
    input_assets: List[str]
    source_evidence: List[str]
    status: str
    persistence: AssetPersistence = AssetPersistence.VERSIONED

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["persistence"] = self.persistence.value
        return data


@dataclass
class ManufacturingReport:
    report_id: str
    report_type: str
    created_at: str
    engine: str
    department: str
    production_line: str
    input_asset_count: int
    output_asset_count: int
    quality_score: float
    validation_status: CertificationStatus
    warnings: List[QualityWarning]
    errors: List[str]
    department_boundary: str
    next_stage: Optional[str]
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["validation_status"] = self.validation_status.value
        return data


@dataclass
class FactoryEvent:
    event_id: str
    event_type: str
    created_at: str
    engine: str
    department: str
    production_line: str
    status: str
    input_assets: List[str]
    output_assets: List[str]
    duration_ms: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_plain_data(value: Any) -> Any:
    """Convert dataclasses/enums/nested containers into JSON-safe structures."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_plain_data(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_plain_data(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_plain_data(v) for v in value]
    return value
