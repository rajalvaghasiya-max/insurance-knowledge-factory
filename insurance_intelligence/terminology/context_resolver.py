"""Deterministic context and ambiguity handling for MO-024F.

This layer requires explicit insurer and product context, and product-variant
context whenever the governed candidate is variant-scoped. It never ranks,
guesses, performs fuzzy matching, or uses semantic inference.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from insurance_intelligence.contracts.terminology import (
    InsurerMarketingTerm,
    TerminologyPublicationStatus,
    TerminologyResolutionResult,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.alias_resolver import (
    ExactAliasTerminologyResolver,
)
from insurance_intelligence.terminology.resolver import normalise_terminology_text

_ELIGIBLE_REVIEW_STATUSES = frozenset(
    {TerminologyReviewStatus.HUMAN_APPROVED, TerminologyReviewStatus.PUBLISHED}
)
_ELIGIBLE_PUBLICATION_STATUSES = frozenset(
    {
        TerminologyPublicationStatus.ELIGIBLE,
        TerminologyPublicationStatus.AUTHORITATIVE,
    }
)


class TerminologyContextError(ValueError):
    """Raised when a contextual terminology request is structurally invalid."""


def _optional_text(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise TerminologyContextError(f"{field_name} must be non-empty text when supplied")
    return value.strip()


def _is_active(
    effective_from: date | None,
    effective_to: date | None,
    as_of: date,
) -> bool:
    return not (
        (effective_from is not None and as_of < effective_from)
        or (effective_to is not None and as_of > effective_to)
    )


@dataclass(frozen=True)
class TerminologyContextQuery:
    """Text plus optional product context supplied by the calling layer."""

    text: str
    insurer_id: str | None = None
    product_id: str | None = None
    product_variant_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise TerminologyContextError("text must be non-empty text")
        object.__setattr__(self, "text", self.text.strip())
        object.__setattr__(
            self, "insurer_id", _optional_text(self.insurer_id, "insurer_id")
        )
        object.__setattr__(
            self, "product_id", _optional_text(self.product_id, "product_id")
        )
        object.__setattr__(
            self,
            "product_variant_id",
            _optional_text(self.product_variant_id, "product_variant_id"),
        )


@dataclass(frozen=True)
class ContextualTerminologyResolution:
    """Resolved result or an explicit fail-closed contextual outcome."""

    query: TerminologyContextQuery
    result: TerminologyResolutionResult | None
    reason_codes: tuple[str, ...] = ()
    missing_context: tuple[str, ...] = ()
    candidate_term_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "missing_context", tuple(self.missing_context))
        object.__setattr__(self, "candidate_term_ids", tuple(self.candidate_term_ids))
        if self.result is None and not self.reason_codes:
            raise TerminologyContextError(
                "unresolved contextual results must contain reason_codes"
            )
        if self.result is not None and self.reason_codes:
            raise TerminologyContextError(
                "resolved contextual results must not contain reason_codes"
            )

    @property
    def is_resolved(self) -> bool:
        return self.result is not None and self.result.unresolved is None


@dataclass(frozen=True)
class ContextualTerminologyResolver:
    """Require sufficient context and delegate only one governed candidate."""

    resolver: ExactAliasTerminologyResolver

    def resolve(
        self,
        query: TerminologyContextQuery,
        *,
        as_of: date,
    ) -> ContextualTerminologyResolution:
        candidates = self._text_candidates(query.text, as_of=as_of)
        candidate_ids = tuple(item.term_id for item in candidates)
        if not candidates:
            return ContextualTerminologyResolution(
                query=query,
                result=None,
                reason_codes=("NO_GOVERNED_TERM_OR_ALIAS_MATCH",),
            )

        missing = []
        if query.insurer_id is None:
            missing.append("insurer_id")
        if query.product_id is None:
            missing.append("product_id")
        if query.product_variant_id is None and any(
            item.product_variant_id is not None for item in candidates
        ):
            missing.append("product_variant_id")
        if missing:
            return ContextualTerminologyResolution(
                query=query,
                result=None,
                reason_codes=("MISSING_REQUIRED_PRODUCT_CONTEXT",),
                missing_context=tuple(missing),
                candidate_term_ids=candidate_ids,
            )

        scoped = tuple(
            item
            for item in candidates
            if item.insurer_id == query.insurer_id
            and item.product_id == query.product_id
            and item.product_variant_id == query.product_variant_id
        )
        if not scoped:
            return ContextualTerminologyResolution(
                query=query,
                result=None,
                reason_codes=("NO_GOVERNED_MATCH_FOR_CONTEXT",),
                candidate_term_ids=candidate_ids,
            )
        if len(scoped) > 1:
            return ContextualTerminologyResolution(
                query=query,
                result=None,
                reason_codes=("AMBIGUOUS_GOVERNED_TERMINOLOGY",),
                candidate_term_ids=tuple(item.term_id for item in scoped),
            )

        target = scoped[0]
        contextual_query = replace(
            target,
            term_id=f"context-query:{target.term_id}",
            display_name=query.text,
        )
        result = self.resolver.resolve(contextual_query, as_of=as_of)
        if result.unresolved is not None:
            return ContextualTerminologyResolution(
                query=query,
                result=None,
                reason_codes=("GOVERNED_CANDIDATE_FAILED_RESOLUTION",),
                candidate_term_ids=(target.term_id,),
            )
        return ContextualTerminologyResolution(query=query, result=result)

    def _text_candidates(
        self,
        text: str,
        *,
        as_of: date,
    ) -> tuple[InsurerMarketingTerm, ...]:
        key = normalise_terminology_text(text)
        term_ids = {
            item.term_id
            for item in self.resolver.resolver.marketing_terms
            if normalise_terminology_text(item.display_name) == key
            and _is_active(item.effective_from, item.effective_to, as_of)
            and item.review_status in _ELIGIBLE_REVIEW_STATUSES
            and item.publication_status in _ELIGIBLE_PUBLICATION_STATUSES
        }
        for alias in self.resolver.aliases:
            if normalise_terminology_text(alias.alias_text) != key:
                continue
            if not _is_active(alias.effective_from, alias.effective_to, as_of):
                continue
            if alias.review_status not in _ELIGIBLE_REVIEW_STATUSES:
                continue
            if alias.publication_status not in _ELIGIBLE_PUBLICATION_STATUSES:
                continue
            term_ids.add(alias.term_id)
        return tuple(
            sorted(
                (
                    item
                    for item in self.resolver.resolver.marketing_terms
                    if item.term_id in term_ids
                    and _is_active(item.effective_from, item.effective_to, as_of)
                    and item.review_status in _ELIGIBLE_REVIEW_STATUSES
                    and item.publication_status in _ELIGIBLE_PUBLICATION_STATUSES
                ),
                key=lambda item: item.term_id,
            )
        )


__all__ = [
    "ContextualTerminologyResolution",
    "ContextualTerminologyResolver",
    "TerminologyContextError",
    "TerminologyContextQuery",
]
