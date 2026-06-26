from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib
import json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2)


def stable_hash(data: Any, prefix: str = "mma") -> str:
    raw = stable_json_dumps(data).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(raw).hexdigest()[:24]}"


@dataclass(frozen=True)
class CurrentMentalModel:
    belief: str
    confidence: str
    origin: str
    common_misconceptions: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class TargetMentalModel:
    belief: str
    reasoning: str
    decision_implication: str


@dataclass(frozen=True)
class KnowledgeGap:
    missing_concepts: List[str]
    incorrect_assumptions: List[str]
    incorrect_connections: List[str]
    severity: str


@dataclass(frozen=True)
class TransformationPlan:
    transformation_type: str
    steps: List[str]
    recommended_examples: List[str]
    golden_rule: str


@dataclass(frozen=True)
class DecisionReadiness:
    customer_can: List[str]
    advisor_should_confirm: List[str]
    remaining_risks: List[str]


@dataclass(frozen=True)
class BehaviourGoal:
    expected_question: str
    expected_behaviour: str
    observable_success: str


@dataclass(frozen=True)
class Verification:
    scenario: Dict[str, Any]
    question: str
    correct_answer: str
    common_wrong_answer: str
    why_wrong: str
    confidence_threshold: float


@dataclass(frozen=True)
class MentalModelAsset:
    asset_id: str
    concept_id: str
    concept_name: str
    version: str
    current_mental_model: CurrentMentalModel
    target_mental_model: TargetMentalModel
    knowledge_gap: KnowledgeGap
    transformation_plan: TransformationPlan
    decision_readiness: DecisionReadiness
    behaviour_goal: BehaviourGoal
    verification: Verification
    evidence_traceability: Dict[str, Any]
    transformation_metrics: Dict[str, Any]
    certification_status: str
    factory_signature: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
