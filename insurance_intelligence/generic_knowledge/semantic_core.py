"""Thin canonical semantic backbone for PolicyScna insurance intelligence.

This module intentionally does not duplicate evidence, residue, authority, publication,
or decision-support machinery. It supplies stable semantic identity/version contracts that
existing generic knowledge components can bind to.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError


class SemanticCoreError(GenericKnowledgeContractError):
    """Raised when canonical semantic contracts violate invariants."""


class InsuranceCategory(str, Enum):
    HEALTH = "health"
    MOTOR = "motor"
    LIFE = "life"


_CANONICAL_ID = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticCoreError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class CanonicalConceptIdentity:
    """Immutable product-neutral identity for one insurance semantic concept."""

    canonical_id: str
    category: InsuranceCategory
    concept_semantic_version: str
    fact_schema_id: str
    definition_reference_id: str | None = None

    def __post_init__(self) -> None:
        canonical_id = _text(self.canonical_id, "canonical_id")
        if not _CANONICAL_ID.fullmatch(canonical_id):
            raise SemanticCoreError("canonical_id must be a dotted lowercase semantic identifier")
        if not isinstance(self.category, InsuranceCategory):
            raise SemanticCoreError("category must be an InsuranceCategory")
        if canonical_id.split(".", 1)[0] != self.category.value:
            raise SemanticCoreError("canonical_id namespace must match category")
        object.__setattr__(self, "canonical_id", canonical_id)
        object.__setattr__(
            self,
            "concept_semantic_version",
            _text(self.concept_semantic_version, "concept_semantic_version"),
        )
        object.__setattr__(self, "fact_schema_id", _text(self.fact_schema_id, "fact_schema_id"))
        if self.definition_reference_id is not None:
            object.__setattr__(
                self,
                "definition_reference_id",
                _text(self.definition_reference_id, "definition_reference_id"),
            )


@dataclass(frozen=True)
class OntologyRelease:
    release_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "release_id", _text(self.release_id, "release_id"))


@dataclass(frozen=True)
class ApplicabilitySchemaVersion:
    version_id: str
    common_axes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "version_id", _text(self.version_id, "version_id"))
        if not isinstance(self.common_axes, tuple):
            raise SemanticCoreError("common_axes must be a tuple")
        axes = tuple(_text(axis, "common_axes[]") for axis in self.common_axes)
        if len(axes) != len(set(axes)):
            raise SemanticCoreError("common_axes must not contain duplicates")
        object.__setattr__(self, "common_axes", axes)


HEALTH_WAITING_PERIODS = CanonicalConceptIdentity(
    canonical_id="health.waiting_periods.base",
    category=InsuranceCategory.HEALTH,
    concept_semantic_version="1",
    fact_schema_id="waiting_periods_v1",
)

HEALTH_ONTOLOGY_RELEASE = OntologyRelease("health_ontology_2026_08")
HEALTH_APPLICABILITY_SCHEMA = ApplicabilitySchemaVersion(
    version_id="health_applicability_v1",
    common_axes=("product_reference", "policy_version"),
)


__all__ = [
    "ApplicabilitySchemaVersion",
    "CanonicalConceptIdentity",
    "HEALTH_APPLICABILITY_SCHEMA",
    "HEALTH_ONTOLOGY_RELEASE",
    "HEALTH_WAITING_PERIODS",
    "InsuranceCategory",
    "OntologyRelease",
    "SemanticCoreError",
]
