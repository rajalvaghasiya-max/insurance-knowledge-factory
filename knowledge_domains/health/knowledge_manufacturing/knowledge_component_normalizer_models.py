from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Literal
import hashlib

NORMALIZER_VERSION = "1.0"
NORMALIZED_COMPONENT_COLLECTION_CONTRACT_VERSION = "normalized_knowledge_component_collection_v1.0"

NormalizedComponentType = Literal[
    "title",
    "paragraph",
    "list_item",
    "table",
    "note",
    "reference",
    "metadata",
    "noise",
]

ComponentStatus = Literal[
    "active",
    "noise",
    "metadata",
    "duplicate_shadow",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass
class NormalizationDecision:
    action: str
    reason: str
    confidence: float = 1.0


@dataclass
class NormalizedComponent:
    component_id: str
    component_version: str
    normalized_component_id: str
    normalized_component_version: str
    component_type: NormalizedComponentType
    original_component_type: str
    status: ComponentStatus
    document_id: str
    processed_document_asset_id: str | None
    sequence: int
    normalized_sequence: int
    text: str
    normalized_text: str
    display_text: str
    title_hint: str | None
    source: dict[str, Any]
    original_component_ids: list[str] = field(default_factory=list)
    merged_component_ids: list[str] = field(default_factory=list)
    duplicate_group_id: str | None = None
    duplicate_representative: bool = True
    duplicate_occurrence_count: int = 1
    previous_component_id: str | None = None
    next_component_id: str | None = None
    parent_title_hint: str | None = None
    signals: dict[str, Any] = field(default_factory=dict)
    quality: dict[str, Any] = field(default_factory=dict)
    references: list[dict[str, Any]] = field(default_factory=list)
    normalization_decisions: list[NormalizationDecision] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class NormalizedKnowledgeComponentCollection:
    asset_type: str
    collection_id: str
    collection_version: str
    contract_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    source_collection_id: str | None
    source_collection_path: str | None
    components: list[NormalizedComponent]
    duplicate_index: dict[str, Any]
    noise_index: dict[str, Any]
    statistics: dict[str, Any]
    quality: dict[str, Any]
    validation: dict[str, Any]
    status: str = "manufactured"
    next_stage: str = "knowledge_component_classification"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeComponentNormalizerReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    source_collection_id: str | None
    source_collection_path: str | None
    normalized_collection_id: str
    normalized_collection_path: str | None
    raw_components_received: int
    normalized_components_created: int
    components_merged: int
    duplicate_groups: int
    duplicate_shadow_components: int
    noise_components: int
    metadata_components: int
    active_components: int
    cross_references_preserved: int
    warnings: list[dict[str, Any]]
    quality_score: float
    validation_status: str
    statistics: dict[str, Any]
    next_stage: str = "knowledge_component_classification"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
