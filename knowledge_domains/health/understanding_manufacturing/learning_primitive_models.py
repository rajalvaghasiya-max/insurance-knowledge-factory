"""
PolicyScna Department V — Learning Primitive Models v1.0

A Learning Primitive is the smallest reusable unit that increases a person's
understanding of one specific aspect of an insurance concept.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LearningPrimitiveType(str, Enum):
    DEFINITION = "definition"
    MEANING = "meaning"
    MONEY_FLOW = "money_flow"
    WORKED_EXAMPLE = "worked_example"
    MISCONCEPTION = "misconception"
    PURPOSE = "purpose"
    SUITABILITY = "suitability"
    RELATED_CONCEPTS = "related_concepts"
    FAQ = "faq"
    ADVISOR_NOTE = "advisor_note"
    WARNING = "warning"


@dataclass(frozen=True)
class LearningPrimitive:
    primitive_id: str
    primitive_type: str
    concept_id: str
    concept_name: str
    learning_objective: str
    content: Dict[str, Any]
    delivery_tags: List[str]
    difficulty: str = "basic"
    prerequisites: List[str] = field(default_factory=list)
    related_primitives: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    source_meaning_fields: List[str] = field(default_factory=list)
    confidence: float = 1.0
    review_status: str = "approved"
    status: str = "certified_candidate"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearningPrimitiveCollection:
    asset_id: str
    asset_type: str
    collection_id: str
    collection_version: str
    schema_version: str
    department_boundary: str
    concept_id: str
    concept_name: str
    source_meaning_asset_id: str
    source_meaning_asset_type: str
    primitives: List[LearningPrimitive]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["primitives"] = [primitive.to_dict() for primitive in self.primitives]
        return data
