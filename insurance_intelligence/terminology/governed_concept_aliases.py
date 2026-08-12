"""Governed exact alias membership for comparison-critical canonical concept identity.

MO-024 concept resolution already provides deterministic exact matching and explicit
ambiguity. MO-028C adds the missing governance edge: a label may act as a
comparison-authoritative canonical concept alias only when that membership has its
own evidence, review decision, governance version, and immutable snapshot identity.

This module does not perform fuzzy matching, embeddings, LLM inference, hierarchy,
product-specific branching, comparison, or runtime self-learning.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from hashlib import sha256

from insurance_intelligence.contracts.terminology import (
    EvidenceSpan,
    TerminologyPublicationStatus,
    TerminologyReviewStatus,
)
from insurance_intelligence.terminology.concept_registry import (
    CanonicalConceptDefinition,
    CanonicalConceptRegistry,
)
from insurance_intelligence.terminology.resolver import normalise_terminology_text


class GovernedConceptAliasError(ValueError):
    """Raised when governed canonical-concept alias state is invalid."""


class BenefitConceptIdentityStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    NOT_FOUND = "NOT_FOUND"
    INVALID_INPUT = "INVALID_INPUT"


_ELIGIBLE_REVIEW_STATUSES = frozenset(
    {TerminologyReviewStatus.HUMAN_APPROVED, TerminologyReviewStatus.PUBLISHED}
)
_ELIGIBLE_PUBLICATION_STATUSES = frozenset(
    {TerminologyPublicationStatus.ELIGIBLE, TerminologyPublicationStatus.AUTHORITATIVE}
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GovernedConceptAliasError(f"{label} must be non-empty text")
    return value.strip()


def _is_active(effective_from: date | None, effective_to: date | None, as_of: date) -> bool:
    if effective_from is not None and as_of < effective_from:
        return False
    if effective_to is not None and as_of > effective_to:
        return False
    return True


@dataclass(frozen=True)
class GovernedConceptAlias:
    """One reviewed label-to-canonical-concept membership decision."""

    alias_id: str
    alias_text: str
    concept_id: str
    evidence_spans: tuple[EvidenceSpan, ...]
    review_decision_id: str
    governance_version: str
    review_status: TerminologyReviewStatus
    publication_status: TerminologyPublicationStatus
    effective_from: date | None = None
    effective_to: date | None = None
    source_scope: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "alias_id", _text(self.alias_id, "alias_id"))
        object.__setattr__(self, "alias_text", _text(self.alias_text, "alias_text"))
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        object.__setattr__(
            self, "review_decision_id", _text(self.review_decision_id, "review_decision_id")
        )
        object.__setattr__(
            self, "governance_version", _text(self.governance_version, "governance_version")
        )
        if self.source_scope is not None:
            object.__setattr__(self, "source_scope", _text(self.source_scope, "source_scope"))
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise GovernedConceptAliasError("effective_to must be on or after effective_from")
        if not isinstance(self.evidence_spans, tuple) or not self.evidence_spans:
            raise GovernedConceptAliasError("evidence_spans must contain evidence")
        if not all(isinstance(item, EvidenceSpan) for item in self.evidence_spans):
            raise GovernedConceptAliasError("evidence_spans must contain EvidenceSpan values")
        if (
            self.publication_status is TerminologyPublicationStatus.AUTHORITATIVE
            and self.review_status is not TerminologyReviewStatus.PUBLISHED
        ):
            raise GovernedConceptAliasError(
                "authoritative concept aliases must have PUBLISHED review status"
            )


@dataclass(frozen=True)
class GovernedConceptAliasRegistry:
    """Immutable comparison-authoritative alias layer over CanonicalConceptRegistry."""

    concept_registry: CanonicalConceptRegistry
    aliases: tuple[GovernedConceptAlias, ...]
    registry_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.concept_registry, CanonicalConceptRegistry):
            raise GovernedConceptAliasError("concept_registry must be a CanonicalConceptRegistry")
        object.__setattr__(self, "aliases", tuple(self.aliases))
        object.__setattr__(self, "registry_version", _text(self.registry_version, "registry_version"))
        if not all(isinstance(item, GovernedConceptAlias) for item in self.aliases):
            raise GovernedConceptAliasError("aliases must contain GovernedConceptAlias values")

        alias_ids = tuple(item.alias_id for item in self.aliases)
        if len(alias_ids) != len(set(alias_ids)):
            raise GovernedConceptAliasError("alias_id values must be unique")

        concepts = {item.concept_id: item for item in self.concept_registry.all_concepts()}
        for alias in self.aliases:
            if alias.concept_id not in concepts:
                raise GovernedConceptAliasError(
                    f"alias {alias.alias_id} references unknown concept_id {alias.concept_id}"
                )

        members: dict[str, list[GovernedConceptAlias]] = {}
        for alias in self.aliases:
            members.setdefault(normalise_terminology_text(alias.alias_text), []).append(alias)
        for normalised_label, group in members.items():
            concept_ids = tuple(sorted({item.concept_id for item in group}))
            if len(concept_ids) <= 1:
                continue
            ambiguity_groups = {
                concepts[concept_id].ambiguity_group for concept_id in concept_ids
            }
            if None in ambiguity_groups or len(ambiguity_groups) != 1:
                raise GovernedConceptAliasError(
                    "shared governed concept alias requires one explicit ambiguity_group: "
                    f"{normalised_label}"
                )

    @property
    def snapshot_id(self) -> str:
        payload = "\x1f".join(
            (
                self.registry_version,
                *(item.concept_id for item in self.concept_registry.all_concepts()),
                *(
                    f"{item.alias_id}:{item.concept_id}:{normalise_terminology_text(item.alias_text)}:"
                    f"{item.review_decision_id}:{item.governance_version}"
                    for item in sorted(self.aliases, key=lambda value: value.alias_id)
                ),
            )
        )
        return f"gcar_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True)
class GovernedBenefitConceptResolution:
    status: BenefitConceptIdentityStatus
    raw_label: str
    normalised_label: str | None
    selected_concept: CanonicalConceptDefinition | None
    candidates: tuple[CanonicalConceptDefinition, ...]
    matched_alias_ids: tuple[str, ...]
    matched_review_decision_ids: tuple[str, ...]
    alias_registry_version: str
    alias_registry_snapshot_id: str
    reason_codes: tuple[str, ...]

    @property
    def concept_id(self) -> str | None:
        return self.selected_concept.concept_id if self.selected_concept is not None else None


class GovernedBenefitConceptResolver:
    """Resolve only published/eligible governed aliases to canonical benefit concepts."""

    def __init__(self, registry: GovernedConceptAliasRegistry) -> None:
        if not isinstance(registry, GovernedConceptAliasRegistry):
            raise TypeError("registry must be a GovernedConceptAliasRegistry")
        self._registry = registry

    def resolve(self, raw_label: object, *, as_of: date) -> GovernedBenefitConceptResolution:
        if not isinstance(raw_label, str) or not raw_label.strip():
            return GovernedBenefitConceptResolution(
                status=BenefitConceptIdentityStatus.INVALID_INPUT,
                raw_label=raw_label if isinstance(raw_label, str) else repr(raw_label),
                normalised_label=None,
                selected_concept=None,
                candidates=(),
                matched_alias_ids=(),
                matched_review_decision_ids=(),
                alias_registry_version=self._registry.registry_version,
                alias_registry_snapshot_id=self._registry.snapshot_id,
                reason_codes=("INVALID_LABEL",),
            )

        normalised = normalise_terminology_text(raw_label)
        matches = tuple(
            sorted(
                (
                    alias
                    for alias in self._registry.aliases
                    if normalise_terminology_text(alias.alias_text) == normalised
                    and _is_active(alias.effective_from, alias.effective_to, as_of)
                    and alias.review_status in _ELIGIBLE_REVIEW_STATUSES
                    and alias.publication_status in _ELIGIBLE_PUBLICATION_STATUSES
                ),
                key=lambda item: item.alias_id,
            )
        )
        if not matches:
            return GovernedBenefitConceptResolution(
                status=BenefitConceptIdentityStatus.NOT_FOUND,
                raw_label=raw_label,
                normalised_label=normalised,
                selected_concept=None,
                candidates=(),
                matched_alias_ids=(),
                matched_review_decision_ids=(),
                alias_registry_version=self._registry.registry_version,
                alias_registry_snapshot_id=self._registry.snapshot_id,
                reason_codes=("NO_ELIGIBLE_GOVERNED_ALIAS",),
            )

        concept_ids = tuple(sorted({item.concept_id for item in matches}))
        candidates = tuple(self._registry.concept_registry.get(item) for item in concept_ids)
        alias_ids = tuple(item.alias_id for item in matches)
        review_ids = tuple(sorted({item.review_decision_id for item in matches}))
        if len(candidates) > 1:
            return GovernedBenefitConceptResolution(
                status=BenefitConceptIdentityStatus.AMBIGUOUS,
                raw_label=raw_label,
                normalised_label=normalised,
                selected_concept=None,
                candidates=candidates,
                matched_alias_ids=alias_ids,
                matched_review_decision_ids=review_ids,
                alias_registry_version=self._registry.registry_version,
                alias_registry_snapshot_id=self._registry.snapshot_id,
                reason_codes=("MULTIPLE_GOVERNED_BENEFIT_CONCEPTS",),
            )

        return GovernedBenefitConceptResolution(
            status=BenefitConceptIdentityStatus.RESOLVED,
            raw_label=raw_label,
            normalised_label=normalised,
            selected_concept=candidates[0],
            candidates=candidates,
            matched_alias_ids=alias_ids,
            matched_review_decision_ids=review_ids,
            alias_registry_version=self._registry.registry_version,
            alias_registry_snapshot_id=self._registry.snapshot_id,
            reason_codes=("EXACT_GOVERNED_ALIAS_MATCH",),
        )


def comparison_identity_compatible(
    left: GovernedBenefitConceptResolution,
    right: GovernedBenefitConceptResolution,
) -> bool:
    """G1 v1 fail-closed comparison identity compatibility rule."""
    return (
        left.status is BenefitConceptIdentityStatus.RESOLVED
        and right.status is BenefitConceptIdentityStatus.RESOLVED
        and left.concept_id == right.concept_id
        and left.alias_registry_version == right.alias_registry_version
        and left.alias_registry_snapshot_id == right.alias_registry_snapshot_id
    )


__all__ = [
    "BenefitConceptIdentityStatus",
    "GovernedBenefitConceptResolution",
    "GovernedBenefitConceptResolver",
    "GovernedConceptAlias",
    "GovernedConceptAliasError",
    "GovernedConceptAliasRegistry",
    "comparison_identity_compatible",
]
