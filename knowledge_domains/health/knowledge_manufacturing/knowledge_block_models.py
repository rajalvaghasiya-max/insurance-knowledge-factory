from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Literal
import hashlib

KNOWLEDGE_BLOCK_MANUFACTURING_VERSION = "0.1"
KNOWLEDGE_BLOCK_CONTRACT_VERSION = "knowledge_block_collection_v1.0"

BlockType = Literal[
    "heading_block",
    "paragraph_block",
    "table_block",
    "definition_block",
    "procedure_block",
    "rule_block",
    "note_block",
    "illustration_block",
    "contact_block",
    "metadata_block",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass
class KnowledgeBlockSource:
    document_id: str
    processed_document_asset_id: str | None = None
    source_document_type: str | None = None
    authority_score: int | float | None = None
    section_id: str | None = None
    section_order: int | None = None
    parent_section: str | None = None
    page_number: int | None = None
    page_label: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    start_char: int | None = None
    end_char: int | None = None


@dataclass
class KnowledgeBlockStructure:
    sequence: int
    heading: str | None = None
    sub_heading: str | None = None
    heading_level: int | None = None
    source_section_type: str | None = None
    contains_table: bool = False
    contains_list: bool = False
    contains_numbers: bool = False
    contains_cross_reference: bool = False
    contains_definition: bool = False


@dataclass
class KnowledgeBlockContent:
    title: str | None = None
    text: str = ""
    tables: list[dict[str, Any]] = field(default_factory=list)
    lists: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeBlockReferences:
    cross_references: list[dict[str, Any]] = field(default_factory=list)
    child_blocks: list[str] = field(default_factory=list)
    parent_block: str | None = None
    source_clause_ids: list[str] = field(default_factory=list)


@dataclass
class KnowledgeBlockQuality:
    confidence: float = 1.0
    quality_score: float = 100.0
    warnings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class KnowledgeBlock:
    block_id: str
    block_version: str
    block_type: BlockType
    document_id: str
    processed_document_asset_id: str | None
    structure: KnowledgeBlockStructure
    content: KnowledgeBlockContent
    source: KnowledgeBlockSource
    references: KnowledgeBlockReferences
    quality: KnowledgeBlockQuality
    notes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeBlockCollection:
    asset_type: str
    collection_id: str
    collection_version: str
    contract_version: str
    created_at: str
    department: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    source_asset_path: str | None
    blocks: list[KnowledgeBlock]
    statistics: dict[str, Any]
    quality: dict[str, Any]
    validation: dict[str, Any]
    status: str = "manufactured"
    next_stage: str = "concept_recognition"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeBlockManufacturingReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    collection_id: str
    collection_path: str | None
    blocks_created: int
    orphan_paragraphs: int
    duplicate_blocks: int
    tables_attached: int
    cross_references_preserved: int
    warnings: list[dict[str, Any]]
    quality_score: float
    validation_status: str
    statistics: dict[str, Any]
    next_stage: str = "concept_recognition"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
