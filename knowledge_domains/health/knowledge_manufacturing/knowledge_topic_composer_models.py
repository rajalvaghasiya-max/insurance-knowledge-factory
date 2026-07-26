"""
PolicyScna Department IV - Knowledge Topic Composer Models v1.0

Purpose:
    Define the asset contract for Knowledge Topic Collections.

Boundary:
    This model supports advisor-conversation topic composition only.
    It must not perform concept recognition, canonicalization, or insurance
    semantic interpretation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import hashlib


CONTRACT_VERSION = "knowledge_topic_collection_v1.0"
COMPOSER_VERSION = "1.0"
DEPARTMENT_BOUNDARY = "knowledge_topics_only_no_concept_recognition_no_canonicalization"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(value: str, prefix: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


@dataclass
class TopicCompositionDecision:
    action: str
    reason: str
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AdvisorConversationSlots:
    title: List[str] = field(default_factory=list)
    definition: List[str] = field(default_factory=list)
    purpose: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    limits: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    procedures: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    supporting_details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeTopic:
    topic_id: str
    topic_version: str
    topic_sequence: int
    topic_name: str
    topic_type: str
    primary_business_question: str
    advisor_explanation_goal: str
    status: str
    lifecycle_stage: str
    document_id: str
    processed_document_asset_id: str
    source_classified_collection_id: str
    component_ids: List[str]
    classified_component_ids: List[str]
    component_count: int
    active_component_count: int
    component_role_counts: Dict[str, int]
    advisor_conversation_slots: AdvisorConversationSlots
    evidence: List[Dict[str, Any]]
    references: List[Dict[str, Any]]
    relationships: Dict[str, Any]
    quality: Dict[str, Any]
    composition: Dict[str, Any]
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["advisor_conversation_slots"] = self.advisor_conversation_slots.to_dict()
        return data


@dataclass
class KnowledgeTopicCollection:
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
    source_classified_collection_id: str
    source_classified_collection_path: str
    topics: List[KnowledgeTopic]
    department_boundary: str = DEPARTMENT_BOUNDARY

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["topics"] = [topic.to_dict() for topic in self.topics]
        return data


@dataclass
class KnowledgeTopicComposerReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str
    source_classified_collection_id: str
    source_classified_collection_path: str
    topic_collection_id: str
    topic_collection_path: str
    classified_components_received: int
    components_assigned: int
    components_skipped: int
    topics_created: int
    active_topics: int
    incomplete_topics: int
    orphan_components: int
    average_components_per_topic: float
    largest_topic_component_count: int
    smallest_topic_component_count: int
    average_cohesion_score: float
    topic_type_counts: Dict[str, int]
    warnings: List[Dict[str, Any]]
    quality_score: float
    validation_status: str
    department_boundary: str
    statistics: Dict[str, Any]
    next_stage: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
