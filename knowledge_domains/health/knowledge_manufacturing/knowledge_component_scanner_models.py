from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Literal
import hashlib

SCANNER_VERSION = "1.0"
COMPONENT_COLLECTION_CONTRACT_VERSION = "knowledge_component_collection_v1.0"

RawComponentType = Literal[
    "title",
    "paragraph",
    "list_item",
    "table",
    "note",
    "reference",
    "metadata",
    "noise",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass
class ComponentSource:
    document_id: str
    processed_document_asset_id: str | None = None
    source_document_type: str | None = None
    authority_score: int | float | None = None
    section_id: str | None = None
    section_order: int | None = None
    page_number: int | None = None
    page_label: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    start_char: int | None = None
    end_char: int | None = None


@dataclass
class ComponentScannerSignals:
    source_kind: str | None = None
    structural_signal: str | None = None
    is_heading_like: bool = False
    is_list_like: bool = False
    is_table_like: bool = False
    is_metadata_like: bool = False
    is_noise_like: bool = False
    contains_cross_reference: bool = False
    contains_numbers: bool = False
    paragraph_count: int = 1
    word_count: int = 0


@dataclass
class ComponentQuality:
    confidence: float = 1.0
    quality_score: float = 100.0
    warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeComponent:
    component_id: str
    component_version: str
    component_type: RawComponentType
    document_id: str
    processed_document_asset_id: str | None
    sequence: int
    text: str
    normalized_text: str
    title_hint: str | None
    source: ComponentSource
    signals: ComponentScannerSignals
    quality: ComponentQuality
    references: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeComponentCollection:
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
    source_asset_path: str | None
    components: list[KnowledgeComponent]
    statistics: dict[str, Any]
    quality: dict[str, Any]
    validation: dict[str, Any]
    status: str = "manufactured"
    next_stage: str = "knowledge_component_classification"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeComponentScannerReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    production_line: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    collection_id: str
    collection_path: str | None
    components_created: int
    source_sections_processed: int
    source_tables_processed: int
    duplicate_components: int
    noise_components: int
    cross_references_preserved: int
    warnings: list[dict[str, Any]]
    quality_score: float
    validation_status: str
    statistics: dict[str, Any]
    next_stage: str = "knowledge_component_classification"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
