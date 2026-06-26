from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List
import hashlib
import json

from .observation_models import ObservationRecord


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_hash(data: Any, length: int = 24) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()[:length]


@dataclass(frozen=True)
class KnowledgePotentialScore:
    financial: int = 0
    teaching: int = 0
    behaviour: int = 0
    decision: int = 0
    relationship: int = 0
    emotional: int = 0

    @property
    def overall(self) -> float:
        values = [self.financial, self.teaching, self.behaviour, self.decision, self.relationship, self.emotional]
        return round(sum(values) / len(values), 2)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["overall"] = self.overall
        return data


@dataclass(frozen=True)
class ManufacturingOpportunity:
    asset_type: str
    reason: str
    priority: str = "medium"
    target_department: str = "unassigned"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DistillationReport:
    distillation_id: str
    observation: ObservationRecord
    classification: Dict[str, Any]
    knowledge_potential: KnowledgePotentialScore
    manufacturing_opportunities: List[ManufacturingOpportunity]
    relationships: List[str]
    confidence: float
    review_required: bool
    factory_signature: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        observation: ObservationRecord,
        classification: Dict[str, Any],
        knowledge_potential: KnowledgePotentialScore,
        opportunities: List[ManufacturingOpportunity],
        relationships: List[str],
        confidence: float,
        review_required: bool,
    ) -> "DistillationReport":
        payload = {
            "observation": observation.to_dict(),
            "classification": classification,
            "knowledge_potential": knowledge_potential.to_dict(),
            "opportunities": [o.to_dict() for o in opportunities],
            "relationships": sorted(set(relationships)),
        }
        return DistillationReport(
            distillation_id=f"kdr_{stable_hash(payload)}",
            observation=observation,
            classification=classification,
            knowledge_potential=knowledge_potential,
            manufacturing_opportunities=opportunities,
            relationships=sorted(set(relationships)),
            confidence=confidence,
            review_required=review_required,
            factory_signature={
                "factory": "PolicyScna Knowledge Factory",
                "production_line": "KnowledgeDistillationEngine",
                "version": "1.0",
                "deterministic": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distillation_id": self.distillation_id,
            "observation": self.observation.to_dict(),
            "classification": self.classification,
            "knowledge_potential": self.knowledge_potential.to_dict(),
            "manufacturing_opportunities": [o.to_dict() for o in self.manufacturing_opportunities],
            "relationships": self.relationships,
            "confidence": self.confidence,
            "review_required": self.review_required,
            "factory_signature": self.factory_signature,
        }
