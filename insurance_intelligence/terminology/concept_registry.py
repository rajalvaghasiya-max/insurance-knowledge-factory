"""Canonical insurance concept registry for MO-024A.

This registry sits before product-specific terminology mapping. It models the
insurance concepts a user may be referring to, together with governed exact
aliases. It deliberately does not resolve ambiguity, retrieve evidence, infer
product applicability, compare products, or recommend anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from insurance_intelligence.contracts.reasoning_plan import DOMAIN_VALUES
from insurance_intelligence.contracts.terminology import CanonicalConceptFamily
from insurance_intelligence.terminology.resolver import normalise_terminology_text


CONCEPT_TYPES = frozenset(
    {
        "BENEFIT",
        "COST_SHARING",
        "COVERAGE",
        "ELIGIBILITY",
        "EXCLUSION",
        "LIMIT",
        "WAITING_PERIOD",
        "CLAIM_PROCESS",
        "GENERAL_TERM",
    }
)


class CanonicalConceptRegistryError(ValueError):
    """Raised when canonical concept registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalConceptRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _unique_text(values: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(values, str):
        raise CanonicalConceptRegistryError(f"{label} must be a sequence of strings")
    result = tuple(_text(value, f"{label}[]") for value in values)
    normalised = tuple(normalise_terminology_text(value) for value in result)
    if len(normalised) != len(set(normalised)):
        raise CanonicalConceptRegistryError(f"{label} contains duplicate normalised values")
    return result


@dataclass(frozen=True)
class CanonicalConceptDefinition:
    """Governed language surface for one canonical insurance concept family."""

    concept: CanonicalConceptFamily
    concept_type: str
    aliases: tuple[str, ...] = ()
    customer_phrases: tuple[str, ...] = ()
    insurer_terms: tuple[str, ...] = ()
    ambiguity_group: str | None = None
    downstream_topic: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.concept, CanonicalConceptFamily):
            raise CanonicalConceptRegistryError("concept must be a CanonicalConceptFamily")
        if self.concept.domain not in DOMAIN_VALUES:
            raise CanonicalConceptRegistryError(
                f"concept.domain must be one of {sorted(DOMAIN_VALUES)}; got {self.concept.domain!r}"
            )
        concept_type = _text(self.concept_type, "concept_type").upper()
        if concept_type not in CONCEPT_TYPES:
            raise CanonicalConceptRegistryError(
                f"concept_type must be one of {sorted(CONCEPT_TYPES)}; got {concept_type!r}"
            )
        object.__setattr__(self, "concept_type", concept_type)
        object.__setattr__(self, "aliases", _unique_text(self.aliases, "aliases"))
        object.__setattr__(
            self,
            "customer_phrases",
            _unique_text(self.customer_phrases, "customer_phrases"),
        )
        object.__setattr__(
            self,
            "insurer_terms",
            _unique_text(self.insurer_terms, "insurer_terms"),
        )
        if self.ambiguity_group is not None:
            object.__setattr__(
                self,
                "ambiguity_group",
                _text(self.ambiguity_group, "ambiguity_group"),
            )
        if self.downstream_topic is not None:
            object.__setattr__(
                self,
                "downstream_topic",
                _text(self.downstream_topic, "downstream_topic"),
            )

    @property
    def concept_id(self) -> str:
        return self.concept.concept_family_id

    @property
    def domain(self) -> str:
        return self.concept.domain

    def language_keys(self) -> tuple[str, ...]:
        values = (
            self.concept.canonical_name,
            *self.aliases,
            *self.customer_phrases,
            *self.insurer_terms,
        )
        return tuple(sorted(set(normalise_terminology_text(value) for value in values)))


class CanonicalConceptRegistry:
    """Deterministic immutable-by-interface registry of canonical concepts."""

    def __init__(self, concepts: Iterable[CanonicalConceptDefinition] = ()) -> None:
        definitions = tuple(concepts)
        if any(not isinstance(item, CanonicalConceptDefinition) for item in definitions):
            raise CanonicalConceptRegistryError(
                "concepts must contain CanonicalConceptDefinition values"
            )

        by_id: dict[str, CanonicalConceptDefinition] = {}
        canonical_names: set[tuple[str, str]] = set()
        for definition in definitions:
            if definition.concept_id in by_id:
                raise CanonicalConceptRegistryError(
                    f"duplicate concept_id: {definition.concept_id}"
                )
            canonical_key = (
                definition.domain,
                normalise_terminology_text(definition.concept.canonical_name),
            )
            if canonical_key in canonical_names:
                raise CanonicalConceptRegistryError(
                    "canonical concept names must be unique within a domain"
                )
            by_id[definition.concept_id] = definition
            canonical_names.add(canonical_key)

        self._concepts = by_id
        self._phrase_index: dict[tuple[str, str], tuple[str, ...]] = {}
        phrase_members: dict[tuple[str, str], list[str]] = {}
        for definition in definitions:
            for language_key in definition.language_keys():
                phrase_members.setdefault((definition.domain, language_key), []).append(
                    definition.concept_id
                )

        for key, concept_ids in phrase_members.items():
            unique_ids = tuple(sorted(set(concept_ids)))
            if len(unique_ids) > 1:
                groups = {
                    self._concepts[concept_id].ambiguity_group
                    for concept_id in unique_ids
                }
                if None in groups or len(groups) != 1:
                    raise CanonicalConceptRegistryError(
                        "shared terminology within a domain requires one explicit ambiguity_group"
                    )
            self._phrase_index[key] = unique_ids

    def all_concepts(self) -> tuple[CanonicalConceptDefinition, ...]:
        return tuple(self._concepts[key] for key in sorted(self._concepts))

    def get(self, concept_id: str) -> CanonicalConceptDefinition:
        key = _text(concept_id, "concept_id")
        try:
            return self._concepts[key]
        except KeyError as exc:
            raise CanonicalConceptRegistryError(f"concept_id not registered: {key}") from exc

    def candidates_for_phrase(
        self,
        phrase: str,
        *,
        domain: str | None = None,
    ) -> tuple[CanonicalConceptDefinition, ...]:
        key = normalise_terminology_text(_text(phrase, "phrase"))
        if domain is not None:
            validated_domain = _text(domain, "domain")
            if validated_domain not in DOMAIN_VALUES:
                raise CanonicalConceptRegistryError(
                    f"domain must be one of {sorted(DOMAIN_VALUES)}; got {validated_domain!r}"
                )
            ids = self._phrase_index.get((validated_domain, key), ())
        else:
            ids = tuple(
                sorted(
                    {
                        concept_id
                        for (candidate_domain, candidate_key), concept_ids in self._phrase_index.items()
                        if candidate_key == key
                        for concept_id in concept_ids
                    }
                )
            )
        return tuple(self._concepts[concept_id] for concept_id in ids)
