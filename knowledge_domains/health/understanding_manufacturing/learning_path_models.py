"""
PolicyScna Department V — Learning Path Models v1.0

A Learning Path is a deterministic sequence of Learning Primitives designed
for one learning goal and one delivery context.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class LearningPathStep:
    step_number: int
    primitive_id: str
    primitive_type: str
    mandatory: bool
    learning_objective: str
    completion_condition: str = "consume_primitive"
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearningPath:
    path_id: str
    path_type: str
    path_name: str
    concept_id: str
    concept_name: str
    learning_goal: str
    target_persona: str
    delivery_context: str
    estimated_duration_seconds: int
    difficulty: str
    steps: List[LearningPathStep]
    success_criteria: List[str]
    recommended_next_paths: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    status: str = "certified_candidate"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["steps"] = [step.to_dict() for step in self.steps]
        return data


@dataclass(frozen=True)
class LearningPathCollection:
    asset_id: str
    asset_type: str
    collection_id: str
    collection_version: str
    schema_version: str
    department_boundary: str
    concept_id: str
    concept_name: str
    source_learning_primitive_collection_id: str
    source_learning_primitive_asset_type: str
    paths: List[LearningPath]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["paths"] = [path.to_dict() for path in self.paths]
        return data
