"""Thin canonical semantic registry for the pre-G11 hardening increment.

The registry defines stable product-neutral concept identity, category namespace,
semantic version, ontology release, applicability schema version, and resolution
hints. It deliberately does not store product facts, assessment policy, or source
governance logic; those remain in the existing G0-G10 layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError


class SemanticRegistryError(GenericKnowledgeContractError):
    """Raised when canonical semantic-registry data violates an invariant."""


class InsuranceCategory(str, Enum):
    HEALTH = "health"
    MOTOR = "motor"
    LIFE = "life"


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticRegistryError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise SemanticRegistryError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, field_name) for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise SemanticRegistryError(f"{field_name} must not contain duplicates")
    return cleaned


@dataclass(frozen=True)
class ApplicabilitySchema:
    """Versioned declaration of applicability dimensions relevant to a concept.

    ``common_axes`` covers stable first-class dimensions. ``extension_axes`` allows
    governed product/domain expansion without making the core schema closed-world.
    Changing either set requires a new schema version and therefore can invalidate
    prior residue-clearance claims through publication dependency binding.
    """

    schema_id: str
    version: str
    common_axes: tuple[str, ...] = ()
    extension_axes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_id", _text(self.schema_id, "schema_id"))
        object.__setattr__(self, "version", _text(self.version, "version"))
        common = _text_tuple(self.common_axes, "common_axes")
        extensions = _text_tuple(self.extension_axes, "extension_axes")
        if set(common) & set(extensions):
            raise SemanticRegistryError("common_axes and extension_axes must not overlap")
        object.__setattr__(self, "common_axes", common)
        object.__setattr__(self, "extension_axes", extensions)

    @property
    def axes(self) -> tuple[str, ...]:
        return self.common_axes + self.extension_axes


@dataclass(frozen=True)
class CanonicalConcept:
    """Stable product-neutral semantic identity consumed by G0-G10."""

    canonical_id: str
    category: InsuranceCategory
    concept_version: str
    ontology_release: str
    fact_schema_id: str
    applicability_schema: ApplicabilitySchema
    definition_reference_id: str
    gloss: str
    aliases: tuple[str, ...] = ()
    negative_aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        canonical_id = _text(self.canonical_id, "canonical_id")
        if not isinstance(self.category, InsuranceCategory):
            raise SemanticRegistryError("category must be an InsuranceCategory")
        expected_prefix = f"{self.category.value}."
        if not canonical_id.startswith(expected_prefix):
            raise SemanticRegistryError(
                f"canonical_id must be namespaced under {expected_prefix}"
            )
        object.__setattr__(self, "canonical_id", canonical_id)
        for field_name in (
            "concept_version",
            "ontology_release",
            "fact_schema_id",
            "definition_reference_id",
            "gloss",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not isinstance(self.applicability_schema, ApplicabilitySchema):
            raise SemanticRegistryError("applicability_schema must be an ApplicabilitySchema")
        aliases = _text_tuple(self.aliases, "aliases")
        negative = _text_tuple(self.negative_aliases, "negative_aliases")
        if {value.casefold() for value in aliases} & {value.casefold() for value in negative}:
            raise SemanticRegistryError("aliases and negative_aliases must not overlap")
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "negative_aliases", negative)


class CanonicalConceptRegistry:
    """Immutable index of canonical concepts with fail-closed term resolution."""

    def __init__(self, concepts: tuple[CanonicalConcept, ...]) -> None:
        if not isinstance(concepts, tuple) or not concepts:
            raise SemanticRegistryError("concepts must be a non-empty tuple")
        if not all(type(item) is CanonicalConcept for item in concepts):
            raise SemanticRegistryError("concepts must contain exact CanonicalConcept values")
        ids = tuple(item.canonical_id for item in concepts)
        if len(ids) != len(set(ids)):
            raise SemanticRegistryError("canonical_id values must be unique")
        self._by_id = {item.canonical_id: item for item in concepts}
        self._concepts = tuple(sorted(concepts, key=lambda item: item.canonical_id))

    @property
    def concepts(self) -> tuple[CanonicalConcept, ...]:
        return self._concepts

    def get(self, canonical_id: str) -> CanonicalConcept | None:
        return self._by_id.get(_text(canonical_id, "canonical_id"))

    def resolve_term(self, term: str, *, category: InsuranceCategory) -> CanonicalConcept:
        """Resolve an exact canonical id or governed alias; ambiguity fails closed."""
        term = _text(term, "term")
        if not isinstance(category, InsuranceCategory):
            raise SemanticRegistryError("category must be an InsuranceCategory")
        folded = term.casefold()
        candidates: list[CanonicalConcept] = []
        for concept in self._concepts:
            if concept.category is not category:
                continue
            if folded == concept.canonical_id.casefold() or folded in {
                alias.casefold() for alias in concept.aliases
            }:
                candidates.append(concept)
        if len(candidates) != 1:
            state = "unresolved" if not candidates else "ambiguous"
            raise SemanticRegistryError(f"canonical term resolution {state}: {term}")
        concept = candidates[0]
        if folded in {value.casefold() for value in concept.negative_aliases}:
            raise SemanticRegistryError(f"term is explicitly not a synonym: {term}")
        return concept


__all__ = [
    "ApplicabilitySchema",
    "CanonicalConcept",
    "CanonicalConceptRegistry",
    "InsuranceCategory",
    "SemanticRegistryError",
]
