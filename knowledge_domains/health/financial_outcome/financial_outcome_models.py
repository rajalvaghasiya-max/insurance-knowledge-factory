from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, payload: str) -> str:
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    concept_id: str
    concept_name: str
    hospital_bill: float
    non_medical_expenses: float
    copay_percent: float
    medical_event: str = "Hospitalization"
    claim_mode: str = "cashless"
    hospital_type: str = "network_hospital"
    city_zone: str = "standard"
    assumptions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClaimAdjudication:
    rule_id: str
    rule_name: str
    hospital_bill: float
    non_medical_expenses: float
    admissible_claim: float
    explanation: str


@dataclass(frozen=True)
class PolicyAdjustment:
    rule_id: str
    adjustment_type: str
    base_amount: float
    percentage: float
    adjustment_amount: float
    reason: str


@dataclass(frozen=True)
class FinancialOutcome:
    insurer_pays: float
    customer_pays: float
    customer_share_percent: float
    shock_level: str
    out_of_pocket_breakdown: Dict[str, float]


@dataclass(frozen=True)
class ShockAnalysis:
    rule_ids: List[str]
    shock_percent: float
    shock_level: str
    explanation: str


@dataclass(frozen=True)
class QualityReport:
    checks: Dict[str, bool]
    pass_: bool

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pass"] = d.pop("pass_")
        return d


@dataclass(frozen=True)
class Certification:
    certification_id: str
    asset_id: str
    concept_id: str
    status: str
    checks: Dict[str, bool]
    created_at: str


@dataclass(frozen=True)
class FinancialOutcomeAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str
    certification_status: str
    source_assets: Dict[str, Any]
    scenario: Dict[str, Any]
    claim_processing: Dict[str, Any]
    policy_conditions: Dict[str, Any]
    financial_outcome: Dict[str, Any]
    explanation: Dict[str, Any]
    decision_readiness: Dict[str, Any]
    verification: Dict[str, Any]
    certification: Dict[str, Any]
    factory_signature: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
