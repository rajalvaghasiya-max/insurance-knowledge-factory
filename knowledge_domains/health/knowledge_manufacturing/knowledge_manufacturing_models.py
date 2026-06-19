from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Literal
import hashlib

KNOWLEDGE_MANUFACTURING_VERSION = "0.1"
CONCEPT_RECOGNITION_CONTRACT_VERSION = "concept_recognition_report_v1.0"

RecognitionDecision = Literal["auto_approved", "review_required", "unknown_concept"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, value: str, length: int = 24) -> str:
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass
class EvidenceReference:
    document_id: str
    processed_document_asset_id: str | None = None
    section_id: str | None = None
    clause_id: str | None = None
    page_number: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    quote: str | None = None
    source_document_type: str | None = None
    authority_score: int | float | None = None


@dataclass
class ConceptCandidate:
    canonical_id: str
    display_name: str
    category: str
    confidence: float
    signals: dict[str, float]
    matched_aliases: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass
class RecognizedConcept:
    recognition_id: str
    text: str
    normalized_text: str
    source_kind: str
    semantic_type: str | None
    decision: RecognitionDecision
    selected_candidate: ConceptCandidate | None
    candidates: list[ConceptCandidate]
    confidence: float
    evidence: EvidenceReference
    notes: list[str] = field(default_factory=list)


@dataclass
class UnknownConceptCandidate:
    unknown_id: str
    text: str
    normalized_text: str
    reason: str
    evidence: EvidenceReference
    suggested_candidates: list[ConceptCandidate] = field(default_factory=list)
    status: str = "pending_review"


@dataclass
class ConceptReviewItem:
    review_id: str
    term: str
    normalized_term: str
    document_id: str
    processed_document_asset_id: str | None
    suggested_canonical_id: str | None
    confidence: float
    reason: str
    evidence: EvidenceReference
    status: str = "pending_human_review"
    reviewer_notes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)


@dataclass
class ConceptRecognitionReport:
    report_type: str
    report_id: str
    report_version: str
    contract_version: str
    created_at: str
    department: str
    engine: str
    document_id: str
    processed_document_asset_id: str | None
    source_asset_path: str | None
    recognized_concepts: list[RecognizedConcept]
    unknown_concepts: list[UnknownConceptCandidate]
    review_items: list[ConceptReviewItem]
    statistics: dict[str, Any]
    thresholds: dict[str, float]
    next_stage: str = "canonicalization"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
