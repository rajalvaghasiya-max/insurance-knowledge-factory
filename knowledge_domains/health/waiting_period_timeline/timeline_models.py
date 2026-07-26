from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict
import hashlib
import json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, payload: Dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass(frozen=True)
class WaitingPeriodTimelineScenario:
    scenario_id: str
    concept_id: str
    concept_name: str
    policy_start_date: str
    claim_date: str
    waiting_period_type: str
    waiting_period_value: int
    waiting_period_unit: str
    activation_convention: str
    assumptions: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimelineAssessment:
    calculated_boundary_date: str
    first_active_date: str
    timeline_status: str
    waiting_period_complete: bool
    explanation: str
    limitation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TimelineQualityReport:
    checks: Dict[str, bool]
    pass_: bool

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["pass"] = payload.pop("pass_")
        return payload


@dataclass(frozen=True)
class TimelineCertification:
    certification_id: str
    asset_id: str
    concept_id: str
    status: str
    checks: Dict[str, bool]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WaitingPeriodTimelineAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str
    certification_status: str
    source_assets: Dict[str, Any]
    scenario: Dict[str, Any]
    timeline_assessment: Dict[str, Any]
    explanation: Dict[str, Any]
    decision_readiness: Dict[str, Any]
    verification: Dict[str, Any]
    certification: Dict[str, Any]
    factory_signature: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)