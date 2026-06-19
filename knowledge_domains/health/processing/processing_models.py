from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Literal
import hashlib
import re


PROCESSING_ASSET_VERSION = "2.0"
PROCESSING_CONTRACT_VERSION = "processed_document_contract_v2.0"

WarningSeverity = Literal["info", "low", "medium", "high", "critical"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ufeff", "")
    text = re.sub(r"[\t\u00a0]+", " ", text)
    text = re.sub(r"[ \u200b\u200c\u200d]{2,}", " ", text)
    # De-hyphenate common PDF line-break artifacts without joining numbered clauses.
    text = re.sub(r"([A-Za-z])\-\n([a-z])", r"\1\2", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def estimate_reading_time_minutes(word_count: int, words_per_minute: int = 225) -> int:
    if word_count <= 0:
        return 0
    return max(1, round(word_count / words_per_minute))


@dataclass
class ProcessingSource:
    document_id: str
    document_type: str | None
    source_type: str | None
    evidence_role: str | None
    authority_score: int | float | None
    relative_path: str
    document_hash: str | None = None
    source_url: str | None = None
    evidence_id: str | None = None
    registry_version: str | None = None
    document_version: str | None = None


@dataclass
class SourceLocation:
    document_id: str
    page_number: int | None = None
    page_label: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    start_char: int | None = None
    end_char: int | None = None
    bbox: dict[str, Any] | None = None


@dataclass
class WarningRecord:
    warning_id: str
    warning_type: str
    severity: WarningSeverity
    message: str
    location: SourceLocation | None = None


@dataclass
class CrossReference:
    reference_id: str
    reference_type: str
    text: str
    normalized_target: str | None
    location: SourceLocation | None = None
    resolved: bool = False


@dataclass
class ProcessedPage:
    page_id: str
    page_number: int
    text: str
    char_count: int
    word_count: int
    line_count: int
    source_location: SourceLocation
    confidence: float = 1.0


@dataclass
class ProcessedSection:
    section_id: str
    title: str
    level: int
    order: int
    text: str
    char_count: int
    word_count: int
    line_count: int
    source_location: SourceLocation
    section_type: str = "unknown"
    heading_level: int | None = None
    contains_table: bool = False
    contains_list: bool = False
    contains_numbers: bool = False
    contains_cross_reference: bool = False
    contains_definition: bool = False
    cross_references: list[CrossReference] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class ProcessedTable:
    table_id: str
    order: int
    rows: list[list[str]]
    row_count: int
    column_count: int
    source_location: SourceLocation
    extraction_method: str = "heuristic"
    confidence: float = 0.75


@dataclass
class ProcessedClause:
    clause_id: str
    order: int
    clause_number: str | None
    text: str
    char_count: int
    source_location: SourceLocation
    extraction_method: str = "heuristic"
    cross_references: list[CrossReference] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class QualityScores:
    overall_score: float
    identity_score: float
    provenance_score: float
    structure_score: float
    validation_score: float
    warning_score: float
    completeness_score: float
    notes: list[str] = field(default_factory=list)


@dataclass
class ProcessingManifest:
    manifest_type: str
    manifest_id: str
    manifest_version: str
    created_at: str
    department: str
    engine: str
    document_id: str
    asset_id: str
    asset_path: str | None
    quality_score: float
    validation_status: str
    warnings_count: int
    critical_warnings_count: int
    engines_used: list[dict[str, str]]
    statistics: dict[str, Any]
    next_department: str = "knowledge_manufacturing"


@dataclass
class CertificationReport:
    report_type: str
    report_id: str
    report_version: str
    created_at: str
    department: str
    document_id: str
    asset_id: str
    certification_status: str
    passed_gates: list[str]
    failed_gates: list[str]
    gate_results: dict[str, Any]
    summary: str


@dataclass
class ProcessedDocumentAsset:
    """
    Processing Asset manufactured by Department III — Document Processing.

    Golden boundary:
        Department III may enrich document structure.
        Department III must never interpret insurance meaning.
    """

    asset_type: str
    asset_id: str
    asset_version: str
    contract_version: str
    processing_engine_version: str
    created_at: str
    document_id: str
    source: ProcessingSource
    normalized_text: str
    pages: list[ProcessedPage] = field(default_factory=list)
    sections: list[ProcessedSection] = field(default_factory=list)
    tables: list[ProcessedTable] = field(default_factory=list)
    clauses: list[ProcessedClause] = field(default_factory=list)
    cross_references: list[CrossReference] = field(default_factory=list)
    statistics: dict[str, Any] = field(default_factory=dict)
    warnings: list[WarningRecord] = field(default_factory=list)
    quality: QualityScores | None = None
    validation: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
