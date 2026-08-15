"""Governed, category-scoped standard-definition contracts for AFR-N1.

This module is deliberately separate from ``concept_registry``.  The existing
terminology registry owns language routing (canonical IDs, names and aliases).
This module owns authoritative definition versions.  It does not map product
facts, infer applicability, retrieve evidence, compare products or recommend.

A standard definition is immutable, category-scoped and valid-time aware.
Consumers must resolve it ``as_of`` a date; there is no timeless "latest"
lookup in the governed contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re


class StandardDefinitionError(ValueError):
    """Raised when a governed definition contract or lookup is invalid."""


class InsuranceCategory(str, Enum):
    HEALTH = "health"
    MOTOR = "motor"
    LIFE = "life"


class DefinitionEvidenceClass(str, Enum):
    PRIMARY_REGULATORY_SOURCE = "PRIMARY_REGULATORY_SOURCE"
    PRIMARY_CONTRACT_SOURCE = "PRIMARY_CONTRACT_SOURCE"


_CONCEPT_ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:[._][a-z0-9]+)+$")
_VERSION_RE = re.compile(r"^[1-9][0-9]*\.[0-9]+(?:\.[0-9]+)?$")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StandardDefinitionError(f"{field_name} must be non-empty text")
    return value.strip()


def _text_tuple(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise StandardDefinitionError(f"{field_name} must be a tuple")
    cleaned = tuple(_text(value, f"{field_name}[]") for value in values)
    normalized = tuple(value.casefold() for value in cleaned)
    if len(normalized) != len(set(normalized)):
        raise StandardDefinitionError(f"{field_name} must not contain duplicates")
    return cleaned


@dataclass(frozen=True)
class DefinitionSourceReference:
    """Primary source identity for one definition version."""

    source_id: str
    authority: str
    locator: str
    source_title: str

    def __post_init__(self) -> None:
        for field_name in ("source_id", "authority", "locator", "source_title"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))


@dataclass(frozen=True)
class GovernedStandardDefinition:
    """One immutable, valid-time definition of one category-scoped concept."""

    definition_id: str
    canonical_concept_id: str
    category: InsuranceCategory
    version: str
    standard_definition: str
    source: DefinitionSourceReference
    evidence_class: DefinitionEvidenceClass
    effective_from: date
    effective_to: date | None = None
    aliases: tuple[str, ...] = ()
    not_synonyms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "definition_id", _text(self.definition_id, "definition_id"))
        concept_id = _text(self.canonical_concept_id, "canonical_concept_id").lower()
        if not _CONCEPT_ID_RE.fullmatch(concept_id):
            raise StandardDefinitionError("canonical_concept_id has invalid format")
        object.__setattr__(self, "canonical_concept_id", concept_id)
        if not isinstance(self.category, InsuranceCategory):
            raise StandardDefinitionError("category must be an InsuranceCategory")
        if not concept_id.startswith(f"{self.category.value}."):
            raise StandardDefinitionError(
                "canonical_concept_id must be namespaced by insurance category"
            )
        version = _text(self.version, "version")
        if not _VERSION_RE.fullmatch(version):
            raise StandardDefinitionError("version must be a positive semantic version")
        object.__setattr__(self, "version", version)
        object.__setattr__(
            self,
            "standard_definition",
            _text(self.standard_definition, "standard_definition"),
        )
        if not isinstance(self.source, DefinitionSourceReference):
            raise StandardDefinitionError("source must be a DefinitionSourceReference")
        if not isinstance(self.evidence_class, DefinitionEvidenceClass):
            raise StandardDefinitionError("evidence_class must be a DefinitionEvidenceClass")
        if not isinstance(self.effective_from, date):
            raise StandardDefinitionError("effective_from must be a date")
        if self.effective_to is not None and not isinstance(self.effective_to, date):
            raise StandardDefinitionError("effective_to must be a date or None")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise StandardDefinitionError("effective_to cannot precede effective_from")
        aliases = _text_tuple(self.aliases, "aliases")
        not_synonyms = _text_tuple(self.not_synonyms, "not_synonyms")
        overlap = {value.casefold() for value in aliases} & {
            value.casefold() for value in not_synonyms
        }
        if overlap:
            raise StandardDefinitionError("aliases and not_synonyms must not overlap")
        object.__setattr__(self, "aliases", aliases)
        object.__setattr__(self, "not_synonyms", not_synonyms)

    def applies_on(self, as_of: date) -> bool:
        if not isinstance(as_of, date):
            raise StandardDefinitionError("as_of must be a date")
        return self.effective_from <= as_of and (
            self.effective_to is None or as_of <= self.effective_to
        )


class StandardDefinitionRegistry:
    """Reference-never-mutate registry with deterministic valid-time lookup."""

    def __init__(self) -> None:
        self._by_id: dict[str, GovernedStandardDefinition] = {}
        self._by_identity: dict[
            tuple[InsuranceCategory, str, str], GovernedStandardDefinition
        ] = {}

    def register(self, definition: GovernedStandardDefinition) -> None:
        if not isinstance(definition, GovernedStandardDefinition):
            raise StandardDefinitionError(
                "definition must be a GovernedStandardDefinition"
            )
        existing_id = self._by_id.get(definition.definition_id)
        if existing_id is not None:
            if existing_id == definition:
                return
            raise StandardDefinitionError(
                "definition_id is immutable; register a new version instead of mutating it"
            )
        identity = (
            definition.category,
            definition.canonical_concept_id,
            definition.version,
        )
        existing_identity = self._by_identity.get(identity)
        if existing_identity is not None and existing_identity != definition:
            raise StandardDefinitionError(
                "category/concept/version identity already exists with different content"
            )
        self._by_id[definition.definition_id] = definition
        self._by_identity[identity] = definition

    def resolve(
        self,
        *,
        category: InsuranceCategory,
        canonical_concept_id: str,
        as_of: date,
    ) -> GovernedStandardDefinition:
        if not isinstance(category, InsuranceCategory):
            raise StandardDefinitionError("category must be an InsuranceCategory")
        concept_id = _text(canonical_concept_id, "canonical_concept_id").lower()
        if not isinstance(as_of, date):
            raise StandardDefinitionError("as_of must be a date")
        matches = tuple(
            definition
            for definition in self._by_id.values()
            if definition.category is category
            and definition.canonical_concept_id == concept_id
            and definition.applies_on(as_of)
        )
        if not matches:
            raise StandardDefinitionError(
                "no governed standard definition is applicable for category/concept/as_of"
            )
        if len(matches) != 1:
            raise StandardDefinitionError(
                "multiple governed standard definitions overlap for category/concept/as_of"
            )
        return matches[0]

    def get(self, definition_id: str) -> GovernedStandardDefinition:
        key = _text(definition_id, "definition_id")
        try:
            return self._by_id[key]
        except KeyError as exc:
            raise StandardDefinitionError(f"unknown definition_id: {key}") from exc

    def all(self) -> tuple[GovernedStandardDefinition, ...]:
        return tuple(sorted(self._by_id.values(), key=lambda item: item.definition_id))


__all__ = [
    "DefinitionEvidenceClass",
    "DefinitionSourceReference",
    "GovernedStandardDefinition",
    "InsuranceCategory",
    "StandardDefinitionError",
    "StandardDefinitionRegistry",
]
