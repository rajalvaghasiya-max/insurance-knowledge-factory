"""Canonical insurance terminology contracts for MO-024A.

These contracts preserve the distinction between a marketing term, a canonical
concept family, and a product-specific implementation. They intentionally do
not perform terminology resolution.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Iterable


class TerminologyContractError(ValueError):
    """Raised when a terminology contract violates a required invariant."""


class TerminologyRelationship(str, Enum):
    EXACT_EQUIVALENT = "EXACT_EQUIVALENT"
    FUNCTIONALLY_SIMILAR = "FUNCTIONALLY_SIMILAR"
    SAME_CONCEPT_DIFFERENT_SCOPE = "SAME_CONCEPT_DIFFERENT_SCOPE"
    BROADER_THAN = "BROADER_THAN"
    NARROWER_THAN = "NARROWER_THAN"
    CONDITIONAL_VARIANT = "CONDITIONAL_VARIANT"
    COMPOSITE_IMPLEMENTATION = "COMPOSITE_IMPLEMENTATION"
    MARKETING_ALIAS_ONLY = "MARKETING_ALIAS_ONLY"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    UNRESOLVED = "UNRESOLVED"


class TerminologyReviewStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    AUTO_VALIDATED = "AUTO_VALIDATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    PUBLISHED = "PUBLISHED"
    WITHDRAWN = "WITHDRAWN"


class TerminologyPublicationStatus(str, Enum):
    NOT_PUBLISHED = "NOT_PUBLISHED"
    ELIGIBLE = "ELIGIBLE"
    AUTHORITATIVE = "AUTHORITATIVE"
    WITHDRAWN = "WITHDRAWN"


class ResolverConfidenceBand(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TerminologyContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _normalise_text_tuple(
    values: Iterable[str] | tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if isinstance(values, str):
        raise TerminologyContractError(f"{field_name} must be a sequence of text values")
    normalised = tuple(_required_text(value, field_name) for value in values)
    if not allow_empty and not normalised:
        raise TerminologyContractError(f"{field_name} must not be empty")
    if len(set(normalised)) != len(normalised):
        raise TerminologyContractError(f"{field_name} must not contain duplicates")
    return normalised


@dataclass(frozen=True)
class EvidenceSpan:
    source_id: str
    document_id: str
    locator: str
    quoted_text: str
    evidence_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _required_text(self.source_id, "source_id"))
        object.__setattr__(
            self, "document_id", _required_text(self.document_id, "document_id")
        )
        object.__setattr__(self, "locator", _required_text(self.locator, "locator"))
        object.__setattr__(
            self, "quoted_text", _required_text(self.quoted_text, "quoted_text")
        )
        if self.evidence_id is not None:
            object.__setattr__(
                self,
                "evidence_id",
                _required_text(self.evidence_id, "evidence_id"),
            )


@dataclass(frozen=True)
class InsurerMarketingTerm:
    term_id: str
    display_name: str
    insurer_id: str
    product_id: str
    product_variant_id: str | None
    effective_from: date | None
    effective_to: date | None
    evidence_spans: tuple[EvidenceSpan, ...]
    review_status: TerminologyReviewStatus
    publication_status: TerminologyPublicationStatus

    def __post_init__(self) -> None:
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
        object.__setattr__(
            self, "display_name", _required_text(self.display_name, "display_name")
        )
        object.__setattr__(
            self, "insurer_id", _required_text(self.insurer_id, "insurer_id")
        )
        object.__setattr__(
            self, "product_id", _required_text(self.product_id, "product_id")
        )
        if self.product_variant_id is not None:
            object.__setattr__(
                self,
                "product_variant_id",
                _required_text(self.product_variant_id, "product_variant_id"),
            )
        if self.effective_from and self.effective_to:
            if self.effective_to < self.effective_from:
                raise TerminologyContractError(
                    "effective_to must not be earlier than effective_from"
                )
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise TerminologyContractError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyContractError(
                "evidence_spans must contain EvidenceSpan values"
            )
        if (
            self.publication_status is TerminologyPublicationStatus.AUTHORITATIVE
            and self.review_status is not TerminologyReviewStatus.PUBLISHED
        ):
            raise TerminologyContractError(
                "authoritative terms must have PUBLISHED review status"
            )


@dataclass(frozen=True)
class CanonicalConceptFamily:
    concept_family_id: str
    canonical_name: str
    definition: str
    domain: str
    concept_subtype: str | None = None
    parent_concept_family_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "concept_family_id",
            _required_text(self.concept_family_id, "concept_family_id"),
        )
        object.__setattr__(
            self, "canonical_name", _required_text(self.canonical_name, "canonical_name")
        )
        object.__setattr__(
            self, "definition", _required_text(self.definition, "definition")
        )
        object.__setattr__(self, "domain", _required_text(self.domain, "domain"))
        if self.concept_subtype is not None:
            object.__setattr__(
                self,
                "concept_subtype",
                _required_text(self.concept_subtype, "concept_subtype"),
            )
        if self.parent_concept_family_id is not None:
            parent = _required_text(
                self.parent_concept_family_id, "parent_concept_family_id"
            )
            if parent == self.concept_family_id:
                raise TerminologyContractError(
                    "a concept family cannot be its own parent"
                )
            object.__setattr__(self, "parent_concept_family_id", parent)


@dataclass(frozen=True)
class ProductTermImplementation:
    implementation_id: str
    term_id: str
    concept_family_id: str
    behaviour_signature_id: str | None
    conditions: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_spans: tuple[EvidenceSpan, ...]
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "implementation_id",
            _required_text(self.implementation_id, "implementation_id"),
        )
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
        object.__setattr__(
            self,
            "concept_family_id",
            _required_text(self.concept_family_id, "concept_family_id"),
        )
        if self.behaviour_signature_id is not None:
            object.__setattr__(
                self,
                "behaviour_signature_id",
                _required_text(
                    self.behaviour_signature_id, "behaviour_signature_id"
                ),
            )
        object.__setattr__(
            self,
            "conditions",
            _normalise_text_tuple(self.conditions, "conditions"),
        )
        object.__setattr__(
            self,
            "limitations",
            _normalise_text_tuple(self.limitations, "limitations"),
        )
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise TerminologyContractError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyContractError(
                "evidence_spans must contain EvidenceSpan values"
            )
        if self.effective_from and self.effective_to:
            if self.effective_to < self.effective_from:
                raise TerminologyContractError(
                    "effective_to must not be earlier than effective_from"
                )


@dataclass(frozen=True)
class ResolverConfidence:
    score: float
    band: ResolverConfidenceBand
    rationale: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise TerminologyContractError("score must be numeric")
        score = float(self.score)
        if not 0.0 <= score <= 1.0:
            raise TerminologyContractError("score must be between 0 and 1")
        object.__setattr__(self, "score", score)
        object.__setattr__(
            self,
            "rationale",
            _normalise_text_tuple(self.rationale, "rationale", allow_empty=False),
        )


@dataclass(frozen=True)
class AliasCandidate:
    candidate_id: str
    term_id: str
    candidate_concept_family_id: str
    relationship: TerminologyRelationship
    confidence: ResolverConfidence
    evidence_spans: tuple[EvidenceSpan, ...]
    review_status: TerminologyReviewStatus

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "candidate_id", _required_text(self.candidate_id, "candidate_id")
        )
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
        object.__setattr__(
            self,
            "candidate_concept_family_id",
            _required_text(
                self.candidate_concept_family_id,
                "candidate_concept_family_id",
            ),
        )
        if self.relationship is TerminologyRelationship.UNRESOLVED:
            raise TerminologyContractError(
                "AliasCandidate relationship must be a concrete candidate relationship"
            )
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise TerminologyContractError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyContractError(
                "evidence_spans must contain EvidenceSpan values"
            )


@dataclass(frozen=True)
class TerminologyRelationshipDecision:
    decision_id: str
    left_implementation_id: str
    right_implementation_id: str
    relationship: TerminologyRelationship
    rationale: tuple[str, ...]
    evidence_spans: tuple[EvidenceSpan, ...]
    review_status: TerminologyReviewStatus
    publication_status: TerminologyPublicationStatus

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_id", _required_text(self.decision_id, "decision_id")
        )
        left = _required_text(
            self.left_implementation_id, "left_implementation_id"
        )
        right = _required_text(
            self.right_implementation_id, "right_implementation_id"
        )
        if left == right:
            raise TerminologyContractError(
                "relationship decision requires two different implementations"
            )
        object.__setattr__(self, "left_implementation_id", left)
        object.__setattr__(self, "right_implementation_id", right)
        object.__setattr__(
            self,
            "rationale",
            _normalise_text_tuple(self.rationale, "rationale", allow_empty=False),
        )
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise TerminologyContractError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyContractError(
                "evidence_spans must contain EvidenceSpan values"
            )
        if (
            self.publication_status is TerminologyPublicationStatus.AUTHORITATIVE
            and self.review_status is not TerminologyReviewStatus.PUBLISHED
        ):
            raise TerminologyContractError(
                "authoritative relationship decisions must be PUBLISHED"
            )


@dataclass(frozen=True)
class UnresolvedTerminologyRecord:
    unresolved_id: str
    term_id: str
    reason_codes: tuple[str, ...]
    missing_information: tuple[str, ...]
    evidence_spans: tuple[EvidenceSpan, ...]
    review_status: TerminologyReviewStatus = TerminologyReviewStatus.REVIEW_REQUIRED

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "unresolved_id",
            _required_text(self.unresolved_id, "unresolved_id"),
        )
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
        object.__setattr__(
            self,
            "reason_codes",
            _normalise_text_tuple(
                self.reason_codes, "reason_codes", allow_empty=False
            ),
        )
        object.__setattr__(
            self,
            "missing_information",
            _normalise_text_tuple(
                self.missing_information,
                "missing_information",
                allow_empty=False,
            ),
        )
        if not isinstance(self.evidence_spans, tuple):
            raise TerminologyContractError("evidence_spans must be a tuple")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyContractError(
                "evidence_spans must contain EvidenceSpan values"
            )
        if self.review_status is TerminologyReviewStatus.PUBLISHED:
            raise TerminologyContractError(
                "unresolved terminology records cannot be PUBLISHED"
            )


@dataclass(frozen=True)
class TerminologyResolutionResult:
    resolution_id: str
    term: InsurerMarketingTerm
    selected_concept: CanonicalConceptFamily | None
    implementation: ProductTermImplementation | None
    relationship: TerminologyRelationship
    confidence: ResolverConfidence | None
    alias_candidates: tuple[AliasCandidate, ...]
    unresolved: UnresolvedTerminologyRecord | None
    review_status: TerminologyReviewStatus
    publication_status: TerminologyPublicationStatus

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "resolution_id",
            _required_text(self.resolution_id, "resolution_id"),
        )
        if not isinstance(self.alias_candidates, tuple):
            raise TerminologyContractError("alias_candidates must be a tuple")
        if not all(
            isinstance(candidate, AliasCandidate)
            for candidate in self.alias_candidates
        ):
            raise TerminologyContractError(
                "alias_candidates must contain AliasCandidate values"
            )

        is_unresolved = self.relationship is TerminologyRelationship.UNRESOLVED
        if is_unresolved:
            if self.unresolved is None:
                raise TerminologyContractError(
                    "UNRESOLVED results require an unresolved record"
                )
            if any(
                value is not None
                for value in (
                    self.selected_concept,
                    self.implementation,
                    self.confidence,
                )
            ):
                raise TerminologyContractError(
                    "UNRESOLVED results cannot publish a selected mapping"
                )
            if self.publication_status is not TerminologyPublicationStatus.NOT_PUBLISHED:
                raise TerminologyContractError(
                    "UNRESOLVED results must remain NOT_PUBLISHED"
                )
            return

        if self.unresolved is not None:
            raise TerminologyContractError(
                "resolved results cannot include an unresolved record"
            )
        if self.selected_concept is None:
            raise TerminologyContractError(
                "resolved results require a selected concept"
            )
        if self.implementation is None:
            raise TerminologyContractError(
                "resolved results require a product implementation"
            )
        if self.confidence is None:
            raise TerminologyContractError(
                "resolved results require confidence"
            )
        if self.implementation.term_id != self.term.term_id:
            raise TerminologyContractError(
                "implementation term_id must match the resolved term"
            )
        if (
            self.implementation.concept_family_id
            != self.selected_concept.concept_family_id
        ):
            raise TerminologyContractError(
                "implementation concept_family_id must match the selected concept"
            )
        if (
            self.publication_status is TerminologyPublicationStatus.AUTHORITATIVE
            and self.review_status is not TerminologyReviewStatus.PUBLISHED
        ):
            raise TerminologyContractError(
                "authoritative resolution results must be PUBLISHED"
            )
