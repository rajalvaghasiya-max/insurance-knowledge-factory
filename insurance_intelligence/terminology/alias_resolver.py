"""Deterministic exact alias resolution for MO-024E.

This layer maps only explicitly governed alias text to an existing governed
marketing term. It performs no fuzzy matching, token similarity, semantic
inference, LLM calls, ranking, or recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date

from insurance_intelligence.contracts.terminology import (
    EvidenceSpan,
    InsurerMarketingTerm,
    TerminologyPublicationStatus,
    TerminologyResolutionResult,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.resolver import (
    TerminologyResolver,
    normalise_terminology_text,
)

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


class TerminologyAliasError(ValueError):
    """Raised when a governed alias record is invalid."""


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TerminologyAliasError(f"{field_name} must be non-empty text")
    return value.strip()


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


@dataclass(frozen=True)
class GovernedTerminologyAlias:
    """One exact input alias bound to one governed product-scoped term."""

    alias_id: str
    alias_text: str
    term_id: str
    insurer_id: str
    product_id: str
    product_variant_id: str | None
    evidence_spans: tuple[EvidenceSpan, ...]
    review_status: TerminologyReviewStatus
    publication_status: TerminologyPublicationStatus
    effective_from: date | None = None
    effective_to: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias_id", _required_text(self.alias_id, "alias_id"))
        object.__setattr__(
            self, "alias_text", _required_text(self.alias_text, "alias_text")
        )
        object.__setattr__(self, "term_id", _required_text(self.term_id, "term_id"))
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
                raise TerminologyAliasError(
                    "effective_to must be on or after effective_from"
                )
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise TerminologyAliasError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise TerminologyAliasError(
                "evidence_spans must contain EvidenceSpan values"
            )


@dataclass(frozen=True)
class ExactAliasTerminologyResolver:
    """Resolve exact governed aliases before delegating to the base resolver."""

    resolver: TerminologyResolver
    aliases: tuple[GovernedTerminologyAlias, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "aliases", tuple(self.aliases))
        alias_ids = tuple(item.alias_id for item in self.aliases)
        if len(alias_ids) != len(set(alias_ids)):
            raise TerminologyAliasError("alias_id values must be unique")
        term_ids = {item.term_id for item in self.resolver.marketing_terms}
        for alias in self.aliases:
            if alias.term_id not in term_ids:
                raise TerminologyAliasError(
                    f"alias {alias.alias_id} references unknown term_id {alias.term_id}"
                )

    def resolve(
        self,
        term: InsurerMarketingTerm,
        *,
        as_of: date,
    ) -> TerminologyResolutionResult:
        """Resolve a direct term or one unambiguous exact governed alias."""
        direct = self.resolver.resolve(term, as_of=as_of)
        if direct.unresolved is None:
            return direct

        key = normalise_terminology_text(term.display_name)
        matches = tuple(
            sorted(
                (
                    alias
                    for alias in self.aliases
                    if normalise_terminology_text(alias.alias_text) == key
                    and alias.insurer_id == term.insurer_id
                    and alias.product_id == term.product_id
                    and alias.product_variant_id == term.product_variant_id
                    and _is_active(alias.effective_from, alias.effective_to, as_of)
                    and alias.review_status in _ELIGIBLE_REVIEW_STATUSES
                    and alias.publication_status in _ELIGIBLE_PUBLICATION_STATUSES
                ),
                key=lambda alias: alias.alias_id,
            )
        )
        if len(matches) != 1:
            return direct

        alias = matches[0]
        governed_terms = tuple(
            item for item in self.resolver.marketing_terms if item.term_id == alias.term_id
        )
        if len(governed_terms) != 1:
            return direct

        canonical_query = replace(
            term,
            display_name=governed_terms[0].display_name,
        )
        return self.resolver.resolve(canonical_query, as_of=as_of)


__all__ = [
    "ExactAliasTerminologyResolver",
    "GovernedTerminologyAlias",
    "TerminologyAliasError",
]
