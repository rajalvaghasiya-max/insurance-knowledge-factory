"""Semantic dependency binding layered over the certified G7 publication binding.

G7 remains backward compatible. New G11-era publications can additionally bind the
ontology release, individual concept version, applicability schema version, and
mapping-policy version. Any change makes the semantic binding unequal and therefore
requires targeted revalidation rather than silently reusing stale residue clearance.
"""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.generic_knowledge.contracts import GenericKnowledgeContractError
from insurance_intelligence.generic_knowledge.publication_eligibility import (
    PublicationDependencyBinding,
)


class SemanticDependencyError(GenericKnowledgeContractError):
    """Raised when semantic publication dependency data is invalid."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticDependencyError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class SemanticPublicationDependencyBinding:
    base: PublicationDependencyBinding
    ontology_release: str
    canonical_concept_id: str
    concept_version: str
    applicability_schema_version: str
    mapping_policy_version: str
    assessment_policy_version: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.base, PublicationDependencyBinding):
            raise SemanticDependencyError("base must be a PublicationDependencyBinding")
        for field_name in (
            "ontology_release",
            "canonical_concept_id",
            "concept_version",
            "applicability_schema_version",
            "mapping_policy_version",
        ):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if "." not in self.canonical_concept_id:
            raise SemanticDependencyError("canonical_concept_id must be category namespaced")
        if self.assessment_policy_version is not None:
            object.__setattr__(
                self,
                "assessment_policy_version",
                _text(self.assessment_policy_version, "assessment_policy_version"),
            )


def semantic_dependency_matches(
    published: SemanticPublicationDependencyBinding,
    current: SemanticPublicationDependencyBinding,
) -> bool:
    if not isinstance(published, SemanticPublicationDependencyBinding) or not isinstance(
        current, SemanticPublicationDependencyBinding
    ):
        raise SemanticDependencyError(
            "published and current must be SemanticPublicationDependencyBinding values"
        )
    return published == current


__all__ = [
    "SemanticDependencyError",
    "SemanticPublicationDependencyBinding",
    "semantic_dependency_matches",
]
