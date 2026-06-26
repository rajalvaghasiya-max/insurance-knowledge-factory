from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib
import json


FACTORY_NAME = "PolicyScna Knowledge Factory"
PRODUCTION_CELL = "UnderstandingAssetBuilder"
VERSION = "1.0"


def stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


@dataclass(frozen=True)
class UnderstandingCertification:
    certification_id: str
    asset_id: str
    concept_id: str
    status: str
    score: int
    checks: Dict[str, bool]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UnderstandingAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str
    certification_status: str
    reality: str
    common_misunderstanding: str
    root_causes: List[str]
    consequence: str
    example: Dict[str, Any]
    expectation_gap: Dict[str, Any]
    golden_rule: str
    transformation: Dict[str, str]
    verification: Dict[str, Any]
    source_assets: Dict[str, Any]
    certification: Dict[str, Any]
    factory_signature: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def factory_signature() -> Dict[str, Any]:
    return {
        "factory": FACTORY_NAME,
        "production_cell": PRODUCTION_CELL,
        "version": VERSION,
        "deterministic": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
