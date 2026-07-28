"""Immutable governed terminology registry snapshots for MO-024C."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from insurance_intelligence.contracts.terminology import (
    AliasCandidate,
    CanonicalConceptFamily,
    InsurerMarketingTerm,
    ProductTermImplementation,
)
from insurance_intelligence.terminology.resolver import TerminologyResolver


class TerminologyRegistryError(ValueError):
    """Raised when a terminology registry snapshot is internally inconsistent."""


def _duplicate_values(values: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return tuple(sorted(duplicates))


def _stable_snapshot_id(
    marketing_terms: tuple[InsurerMarketingTerm, ...],
    implementations: tuple[ProductTermImplementation, ...],
    concepts: tuple[CanonicalConceptFamily, ...],
    alias_candidates: tuple[AliasCandidate, ...],
) -> str:
    payload = "\x1f".join(
        (
            *(item.term_id for item in sorted(marketing_terms, key=lambda item: item.term_id)),
            *(item.implementation_id for item in sorted(implementations, key=lambda item: item.implementation_id)),
            *(item.concept_family_id for item in sorted(concepts, key=lambda item: item.concept_family_id)),
            *(item.candidate_id for item in sorted(alias_candidates, key=lambda item: item.candidate_id)),
        )
    )
    return f"treg_{sha256(payload.encode('utf-8')).hexdigest()[:24]}"


@dataclass(frozen=True)
class TerminologyRegistrySnapshot:
    """Validated immutable input snapshot for deterministic terminology resolution."""

    marketing_terms: tuple[InsurerMarketingTerm, ...]
    implementations: tuple[ProductTermImplementation, ...]
    concepts: tuple[CanonicalConceptFamily, ...]
    alias_candidates: tuple[AliasCandidate, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "marketing_terms", tuple(self.marketing_terms))
        object.__setattr__(self, "implementations", tuple(self.implementations))
        object.__setattr__(self, "concepts", tuple(self.concepts))
        object.__setattr__(self, "alias_candidates", tuple(self.alias_candidates))
        self._validate_types()
        self._validate_unique_ids()
        self._validate_references()

    @property
    def snapshot_id(self) -> str:
        return _stable_snapshot_id(
            self.marketing_terms,
            self.implementations,
            self.concepts,
            self.alias_candidates,
        )

    def build_resolver(self) -> TerminologyResolver:
        return TerminologyResolver(
            marketing_terms=self.marketing_terms,
            implementations=self.implementations,
            concepts=self.concepts,
            alias_candidates=self.alias_candidates,
        )

    def _validate_types(self) -> None:
        groups = (
            (self.marketing_terms, InsurerMarketingTerm, "marketing_terms"),
            (self.implementations, ProductTermImplementation, "implementations"),
            (self.concepts, CanonicalConceptFamily, "concepts"),
            (self.alias_candidates, AliasCandidate, "alias_candidates"),
        )
        for values, expected_type, field_name in groups:
            if not all(isinstance(value, expected_type) for value in values):
                raise TerminologyRegistryError(
                    f"{field_name} must contain only {expected_type.__name__} values"
                )

    def _validate_unique_ids(self) -> None:
        groups = (
            (tuple(item.term_id for item in self.marketing_terms), "term_id"),
            (
                tuple(item.implementation_id for item in self.implementations),
                "implementation_id",
            ),
            (
                tuple(item.concept_family_id for item in self.concepts),
                "concept_family_id",
            ),
            (tuple(item.candidate_id for item in self.alias_candidates), "candidate_id"),
        )
        for values, field_name in groups:
            duplicates = _duplicate_values(values)
            if duplicates:
                raise TerminologyRegistryError(
                    f"duplicate {field_name} values: {', '.join(duplicates)}"
                )

    def _validate_references(self) -> None:
        term_ids = {item.term_id for item in self.marketing_terms}
        concept_ids = {item.concept_family_id for item in self.concepts}

        for implementation in self.implementations:
            if implementation.term_id not in term_ids:
                raise TerminologyRegistryError(
                    f"implementation {implementation.implementation_id} references unknown term_id {implementation.term_id}"
                )
            if implementation.concept_family_id not in concept_ids:
                raise TerminologyRegistryError(
                    f"implementation {implementation.implementation_id} references unknown concept_family_id {implementation.concept_family_id}"
                )

        for candidate in self.alias_candidates:
            if candidate.term_id not in term_ids:
                raise TerminologyRegistryError(
                    f"alias candidate {candidate.candidate_id} references unknown term_id {candidate.term_id}"
                )
            if candidate.candidate_concept_family_id not in concept_ids:
                raise TerminologyRegistryError(
                    f"alias candidate {candidate.candidate_id} references unknown concept_family_id {candidate.candidate_concept_family_id}"
                )
