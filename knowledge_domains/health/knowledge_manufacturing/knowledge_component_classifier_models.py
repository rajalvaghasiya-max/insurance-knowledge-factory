"""
PolicyScna Department IV - Knowledge Component Classifier Models v1.0

Purpose:
    Define the asset contract for Classified Knowledge Components.

Boundary:
    This model supports document-level component classification only.
    It must not perform insurance semantic interpretation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib


CONTRACT_VERSION = "classified_knowledge_component_collection_v1.0"
CLASSIFIER_VERSION = "1.0"
DEPARTMENT_BOUNDARY = "classified_components_only_no_semantic_insurance_interpretation"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, prefix: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass
class ClassificationDecision:
    action: str
    reason: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComponentClassification:
    classified_type: str
    original_component_type: str
    confidence: float
    classifier_version: str = CLASSIFIER_VERSION
    boundary: str = DEPARTMENT_BOUNDARY
    reasons: List[str] = field(default_factory=list)
    decisions: List[ClassificationDecision] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["decisions"] = [d.to_dict() for d in self.decisions]
        return data


@dataclass
class ClassifiedKnowledgeComponent:
    classified_component_id: str
    classified_component_version: str
    normalized_component_id: str
    normalized_component_version: str
    component_id: str
    component_version: str
    component_type: str
    original_component_type: str
    classified_type: str
    status: str
    document_id: str
    processed_document_asset_id: str
    sequence: int
    normalized_sequence: int
    classified_sequence: int
    text: str
    normalized_text: str
    display_text: str
    title_hint: Optional[str]
    source: Dict[str, Any]
    original_component_ids: List[str]
    merged_component_ids: List[str]
    duplicate_group_id: Optional[str]
    duplicate_representative: bool
    duplicate_occurrence_count: int
    previous_component_id: Optional[str]
    next_component_id: Optional[str]
    previous_classified_component_id: Optional[str]
    next_classified_component_id: Optional[str]
    parent_title_hint: Optional[str]
    signals: Dict[str, Any]
    quality: Dict[str, Any]
    references: List[Dict[str, Any]]
    normalization_decisions: List[Dict[str, Any]]
    classification: ComponentClassification
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["classification"] = self.classification.to_dict()
        return data


@dataclass
class ClassifiedKnowledgeComponentCollection:
    asset_type: str
    collection_id: str
    collection_version: str
    contract_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str
    source_normalized_collection_id: str
    source_normalized_collection_path: str
    components: List[ClassifiedKnowledgeComponent]
    department_boundary: str = DEPARTMENT_BOUNDARY

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["components"] = [c.to_dict() for c in self.components]
        return data


@dataclass
class KnowledgeComponentClassifierReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str
    source_normalized_collection_id: str
    source_normalized_collection_path: str
    classified_collection_id: str
    classified_collection_path: str
    normalized_components_received: int
    classified_components_created: int
    active_components: int
    duplicate_shadow_components: int
    noise_components: int
    metadata_components: int
    classification_type_counts: Dict[str, int]
    low_confidence_components: int
    warnings: List[Dict[str, Any]]
    quality_score: float
    validation_status: str
    department_boundary: str
    statistics: Dict[str, Any]
    next_stage: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
