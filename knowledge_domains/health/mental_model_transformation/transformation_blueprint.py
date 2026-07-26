from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .mental_model_models import (
    CurrentMentalModel,
    TargetMentalModel,
    KnowledgeGap,
    TransformationPlan,
    DecisionReadiness,
    BehaviourGoal,
    Verification,
)


@dataclass
class TransformationBlueprint:
    concept_id: str
    concept_name: str
    source_distillation_id: str
    source_observation_id: str
    source_report: Dict[str, Any]
    inspection: Dict[str, Any] = field(default_factory=dict)
    current_model: Optional[CurrentMentalModel] = None
    target_model: Optional[TargetMentalModel] = None
    knowledge_gap: Optional[KnowledgeGap] = None
    transformation_plan: Optional[TransformationPlan] = None
    decision_readiness: Optional[DecisionReadiness] = None
    behaviour_goal: Optional[BehaviourGoal] = None
    verification: Optional[Verification] = None
    status: str = "initialized"
    station_log: List[str] = field(default_factory=list)

    def log(self, station: str) -> None:
        self.station_log.append(station)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
