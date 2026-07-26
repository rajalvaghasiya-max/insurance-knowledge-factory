"""P2.5-B canonical fact and evidence model v1.

This module defines contracts only. It does not migrate, publish, or mutate
existing Factory artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Optional, Tuple


class ValidationStatus(str, Enum):
    CANDIDATE = "candidate"
    EVIDENCE_ROUTED = "evidence_routed"
    EVIDENCE_ASSEMBLED = "evidence_assembled"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class PublicationStatus(str, Enum):
    UNPUBLISHED = "unpublished"
    AUTHORITATIVE = "authoritative"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class KnowledgeAssertionKind(str, Enum):
    SCALAR_FACT = "scalar_fact"
    CONDITIONAL_RULE = "conditional_rule"


@dataclass(frozen=True)
class Insurer:
    insurer_id: str
    legal_name: str
    insurer_type: Optional[str] = None


@dataclass(frozen=True)
class ProductIdentity:
    """Stable identity for an insurance product or product family.

    product_id must not encode document version, capture date, or storage path.
    UIN is optional because it may be unknown, absent, or version-specific.
    """

    product_id: str
    insurer_id: str
    domain: str
    product_name: str
    uin: Optional[str] = None
    product_family_name: Optional[str] = None


@dataclass(frozen=True)
class ProductVersion:
    """A particular effective configuration of a ProductIdentity."""

    product_version_id: str
    product_id: str
    version_label: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    lifecycle_status: Optional[str] = None


@dataclass(frozen=True)
class SourceDocument:
    """Logical source document independent of any one captured copy."""

    source_document_id: str
    insurer_id: str
    document_type: str
    canonical_title: str
    product_version_id: Optional[str] = None
    source_url: Optional[str] = None


@dataclass(frozen=True)
class DocumentVersion:
    """Immutable captured version of a logical SourceDocument."""

    document_version_id: str
    source_document_id: str
    content_sha256: str
    captured_at: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    storage_locator: Optional[str] = None


@dataclass(frozen=True)
class EvidenceSpan:
    """An immutable span within a DocumentVersion used to support knowledge."""

    evidence_span_id: str
    document_version_id: str
    source_char_start: int
    source_char_end: int
    text_sha256: str
    extraction_method: str
    source_page: Optional[int] = None


@dataclass(frozen=True)
class KnowledgeAssertion:
    """A canonical assertion envelope.

    Payload remains deliberately typed but minimally prescriptive in v1:
    * scalar_fact: requires field_id and value
    * conditional_rule: requires rule_id and rule_type

    Existing detailed ConditionalRule artifacts continue to own rule semantics.
    """

    assertion_id: str
    product_version_id: str
    concept_id: str
    assertion_kind: KnowledgeAssertionKind
    payload: Mapping[str, Any]
    evidence_span_ids: Tuple[str, ...]
    validation_status: ValidationStatus
    publication_status: PublicationStatus = PublicationStatus.UNPUBLISHED
    source_artifact_sha256: Optional[str] = None


@dataclass(frozen=True)
class PublicationDecision:
    """Immutable record of one publication-state decision for an assertion."""

    publication_decision_id: str
    assertion_id: str
    decision_status: PublicationStatus
    decided_at: str
    decision_reason: str
    source_artifact_sha256: Optional[str] = None
    supersedes_publication_decision_id: Optional[str] = None


@dataclass(frozen=True)
class CanonicalBundle:
    """In-memory bundle for validation and future persistence adapters."""

    insurers: Tuple[Insurer, ...] = field(default_factory=tuple)
    product_identities: Tuple[ProductIdentity, ...] = field(default_factory=tuple)
    product_versions: Tuple[ProductVersion, ...] = field(default_factory=tuple)
    source_documents: Tuple[SourceDocument, ...] = field(default_factory=tuple)
    document_versions: Tuple[DocumentVersion, ...] = field(default_factory=tuple)
    evidence_spans: Tuple[EvidenceSpan, ...] = field(default_factory=tuple)
    assertions: Tuple[KnowledgeAssertion, ...] = field(default_factory=tuple)
    publication_decisions: Tuple[PublicationDecision, ...] = field(default_factory=tuple)
