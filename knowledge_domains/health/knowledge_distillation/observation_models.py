from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ObservationRecord:
    observation_id: str
    concept_id: str
    title: str
    observation: str
    category: str = "unknown"
    observation_type: str = "unknown"
    source: str = "unknown"
    confidence: str = "medium"
    frequency: str = "unknown"
    financial_impact: str = "unknown"
    emotional_impact: str = "unknown"
    decision_impact: str = "unknown"
    affected_personas: List[str] = field(default_factory=list)
    linked_concepts: List[str] = field(default_factory=list)
    status: str = "observed"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ObservationRecord":
        return ObservationRecord(
            observation_id=str(data.get("observation_id") or data.get("id") or "UNKNOWN-OBS"),
            concept_id=str(data.get("concept_id") or "unknown"),
            title=str(data.get("title") or "Untitled observation"),
            observation=str(data.get("observation") or data.get("description") or ""),
            category=str(data.get("category") or "unknown"),
            observation_type=str(data.get("observation_type") or data.get("type") or "unknown"),
            source=str(data.get("source") or "unknown"),
            confidence=str(data.get("confidence") or "medium"),
            frequency=str(data.get("frequency") or "unknown"),
            financial_impact=str(data.get("financial_impact") or "unknown"),
            emotional_impact=str(data.get("emotional_impact") or "unknown"),
            decision_impact=str(data.get("decision_impact") or "unknown"),
            affected_personas=list(data.get("affected_personas") or []),
            linked_concepts=list(data.get("linked_concepts") or []),
            status=str(data.get("status") or "observed"),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
