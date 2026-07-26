"""Deterministic, fail-closed terminology resolver for MO-024B.

The resolver deliberately performs no fuzzy matching, semantic inference, LLM
calls, ranking, or recommendation. It selects a mapping only when a single
active, governed term and a single active implementation can be joined to one
canonical concept family.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
import re
import unicodedata
from typing import Iterable

from insurance_intelligence.contracts.terminology import (
    AliasCandidate,
    CanonicalConceptFamily,
    InsurerMarketingTerm,
    ProductTermImplementation,
    ResolverConfidence,
    ResolverConfidenceBand,
    TerminologyPublicationStatus,
    TerminologyRelationship,
    TerminologyResolutionResult,
    TerminologyReviewStatus,
    UnresolvedTerminologyRecord,
)

_WHITESPACE = re.compile(r"\s+")

_ELIGIBLE_REVIEW_STATUSES = frozenset(
    {
        TerminologyReviewStatus.HUMAN_APPROVED,
        TerminologyReviewStatus.PUBLISHED,
    }
)
_ELIGIBLE_PUBLICATION_STATUSES = frozenset(
    {
        TerminologyPublicationStatus.ELIGIBLE,
        TerminologyPublicationStatus.AUTHORITATIVE,
    }
)


def normalise_terminology_text(value: str) -> str:
    """Return a stable exact-match key without performing fuzzy matching."""
    if not isinstance(value, str):
        raise TypeError("terminology text must be a string")
    normalised = unicodedata.normalize("NFKC", value).casefold()
    return _WHITESPACE.sub(" ", normalised).strip()


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join("" if part is None else str(part) for part in parts)
    digest = sha256(payload.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def _is_active(
    effective_from: date | None,
    effective_to: date | None,
    as_of: date,
) -> bool:
    if effective_from is not None and as_of < effective_from:
        return False
    if effective_to is not None and as_of > effective_to:
        return False
    return True


def _variant_matches(query: str | None, candidate: str | None) -> bool:
    return query == candidate


@dataclass(frozen=True)
class TerminologyResolver:
    """Resolve one governed term request against immutable registry snapshots."""

    marketing_terms: tuple[InsurerMarketingTerm, ...]
    implementations: tuple[ProductTermImplementation, ...]
    concepts: tuple[CanonicalConceptFamily, ...]
    alias_candidates: tuple[AliasCandidate, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "marketing_terms", tuple(self.marketing_terms))
        object.__setattr__(self, "implementations", tuple(self.implementations))
        object.__setattr__(self, "concepts", tuple(self.concepts))
        object.__setattr__(self, "alias_candidates", tuple(self.alias_candidates))

    def resolve(
        self,
        term: InsurerMarketingTerm,
        *,
        as_of: date,
    ) -> TerminologyResolutionResult:
        """Resolve ``term`` or return a deterministic unresolved record."""
        resolution_date = as_of
        matches = self._matching_terms(term, resolution_date)

        if not matches:
            return self._unresolved(
                term,
                reason_codes=("NO_MATCHING_GOVERNED_TERM",),
                missing_information=(
                    "A governed active term with the same normalised name and product scope",
                ),
            )

        if len(matches) > 1:
            return self._unresolved(
                term,
                reason_codes=("MULTIPLE_ACTIVE_TERM_RECORDS",),
                missing_information=(
                    "A single authoritative active term record for the requested scope",
                ),
                evidence_spans=self._evidence_from_terms(matches),
            )

        matched_term = matches[0]
        if (
            matched_term.review_status not in _ELIGIBLE_REVIEW_STATUSES
            or matched_term.publication_status not in _ELIGIBLE_PUBLICATION_STATUSES
        ):
            return self._unresolved(
                term,
                reason_codes=("TERM_NOT_GOVERNED_FOR_RESOLUTION",),
                missing_information=(
                    "Human-approved or published term governance",
                    "Eligible or authoritative term publication status",
                ),
                evidence_spans=matched_term.evidence_spans,
            )

        implementations = tuple(
            item
            for item in self.implementations
            if item.term_id == matched_term.term_id
            and _is_active(item.effective_from, item.effective_to, resolution_date)
        )
        if not implementations:
            return self._unresolved(
                term,
                reason_codes=("MISSING_PRODUCT_IMPLEMENTATION",),
                missing_information=(
                    "An active product implementation linked to the governed term",
                ),
                evidence_spans=matched_term.evidence_spans,
            )
        if len(implementations) > 1:
            return self._unresolved(
                term,
                reason_codes=("MULTIPLE_ACTIVE_IMPLEMENTATIONS",),
                missing_information=(
                    "A single active product implementation for the governed term",
                ),
                evidence_spans=self._evidence_from_implementations(implementations),
            )

        implementation = implementations[0]
        concepts = tuple(
            item
            for item in self.concepts
            if item.concept_family_id == implementation.concept_family_id
        )
        if not concepts:
            return self._unresolved(
                term,
                reason_codes=("MISSING_CANONICAL_CONCEPT",),
                missing_information=(
                    "A canonical concept family linked to the active implementation",
                ),
                evidence_spans=implementation.evidence_spans,
            )
        if len(concepts) > 1:
            return self._unresolved(
                term,
                reason_codes=("DUPLICATE_CANONICAL_CONCEPT",),
                missing_information=(
                    "A unique canonical concept family identifier",
                ),
                evidence_spans=implementation.evidence_spans,
            )

        concept = concepts[0]
        confidence = ResolverConfidence(
            score=1.0,
            band=ResolverConfidenceBand.VERY_HIGH,
            rationale=(
                "Exact normalised marketing-term name match",
                "Exact insurer, product, and variant scope match",
                "Single active governed term and product implementation",
                "Canonical concept joined by governed concept-family identifier",
            ),
        )
        candidates = tuple(
            sorted(
                (
                    candidate
                    for candidate in self.alias_candidates
                    if candidate.term_id == matched_term.term_id
                ),
                key=lambda candidate: candidate.candidate_id,
            )
        )
        return TerminologyResolutionResult(
            resolution_id=_stable_id(
                "tres",
                matched_term.term_id,
                implementation.implementation_id,
                concept.concept_family_id,
                resolution_date.isoformat(),
            ),
            term=matched_term,
            selected_concept=concept,
            implementation=implementation,
            relationship=TerminologyRelationship.EXACT_EQUIVALENT,
            confidence=confidence,
            alias_candidates=candidates,
            unresolved=None,
            review_status=matched_term.review_status,
            publication_status=matched_term.publication_status,
        )

    def _matching_terms(
        self,
        query: InsurerMarketingTerm,
        as_of: date,
    ) -> tuple[InsurerMarketingTerm, ...]:
        key = normalise_terminology_text(query.display_name)
        return tuple(
            sorted(
                (
                    item
                    for item in self.marketing_terms
                    if normalise_terminology_text(item.display_name) == key
                    and item.insurer_id == query.insurer_id
                    and item.product_id == query.product_id
                    and _variant_matches(
                        query.product_variant_id, item.product_variant_id
                    )
                    and _is_active(item.effective_from, item.effective_to, as_of)
                ),
                key=lambda item: item.term_id,
            )
        )

    def _unresolved(
        self,
        term: InsurerMarketingTerm,
        *,
        reason_codes: tuple[str, ...],
        missing_information: tuple[str, ...],
        evidence_spans: tuple = (),
    ) -> TerminologyResolutionResult:
        unresolved = UnresolvedTerminologyRecord(
            unresolved_id=_stable_id(
                "tunres",
                term.term_id,
                *reason_codes,
                *missing_information,
            ),
            term_id=term.term_id,
            reason_codes=reason_codes,
            missing_information=missing_information,
            evidence_spans=tuple(evidence_spans),
        )
        return TerminologyResolutionResult(
            resolution_id=_stable_id(
                "tres",
                term.term_id,
                TerminologyRelationship.UNRESOLVED.value,
                *reason_codes,
            ),
            term=term,
            selected_concept=None,
            implementation=None,
            relationship=TerminologyRelationship.UNRESOLVED,
            confidence=None,
            alias_candidates=(),
            unresolved=unresolved,
            review_status=TerminologyReviewStatus.REVIEW_REQUIRED,
            publication_status=TerminologyPublicationStatus.NOT_PUBLISHED,
        )

    @staticmethod
    def _evidence_from_terms(
        terms: Iterable[InsurerMarketingTerm],
    ) -> tuple:
        return tuple(span for term in terms for span in term.evidence_spans)

    @staticmethod
    def _evidence_from_implementations(
        implementations: Iterable[ProductTermImplementation],
    ) -> tuple:
        return tuple(
            span
            for implementation in implementations
            for span in implementation.evidence_spans
        )
