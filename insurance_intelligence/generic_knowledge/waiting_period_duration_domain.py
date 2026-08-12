"""Typed duration-domain references for MO-028B.G11.C6.4.

A schedule-bound waiting-period base mechanic does not duplicate a selected value or a duration
option domain.  It references one governed DURATION_SELECTION semantic fact.  This module owns
that reference contract, cross-fact integrity validation, and publication dependency identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from insurance_intelligence.benefits.waiting_period_contracts import (
    WaitingPeriodScopeType,
    WaitingPeriodType,
    WaitingPeriodValueSource,
)
from insurance_intelligence.generic_knowledge.contracts import (
    ApplicabilityKey,
    GenericKnowledgeContractError,
    SemanticFact,
)


class DurationDomainBindingError(GenericKnowledgeContractError):
    """Raised when a schedule-bound duration-domain reference is invalid."""


def _text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DurationDomainBindingError(f"{field_name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class DurationDomainReference:
    """Stable-enough typed identity for one governed duration-selection semantic fact."""

    semantic_fact_id: str
    waiting_period_type: str
    ontology_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_fact_id", _text(self.semantic_fact_id, "semantic_fact_id"))
        try:
            normalized_type = WaitingPeriodType(str(self.waiting_period_type)).value
        except ValueError as exc:
            raise DurationDomainBindingError(
                "waiting_period_type is not supported by the ontology"
            ) from exc
        object.__setattr__(self, "waiting_period_type", normalized_type)
        object.__setattr__(self, "ontology_version", _text(self.ontology_version, "ontology_version"))

    def as_mapping(self) -> dict[str, str]:
        return {
            "semantic_fact_id": self.semantic_fact_id,
            "waiting_period_type": self.waiting_period_type,
            "ontology_version": self.ontology_version,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "DurationDomainReference":
        if not isinstance(value, Mapping):
            raise DurationDomainBindingError("duration_domain_reference must be a mapping")
        return cls(
            semantic_fact_id=value.get("semantic_fact_id"),
            waiting_period_type=value.get("waiting_period_type"),
            ontology_version=value.get("ontology_version"),
        )


@dataclass(frozen=True)
class DurationDomainDependencyBinding:
    """Publication dependency identity for a referenced schedule-selected duration domain."""

    semantic_fact_id: str
    waiting_period_type: str
    ontology_version: str
    source_document_id: str
    source_document_version: str | None
    source_hash_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "semantic_fact_id", _text(self.semantic_fact_id, "semantic_fact_id"))
        try:
            normalized_type = WaitingPeriodType(str(self.waiting_period_type)).value
        except ValueError as exc:
            raise DurationDomainBindingError(
                "waiting_period_type is not supported by the ontology"
            ) from exc
        object.__setattr__(self, "waiting_period_type", normalized_type)
        object.__setattr__(self, "ontology_version", _text(self.ontology_version, "ontology_version"))
        object.__setattr__(self, "source_document_id", _text(self.source_document_id, "source_document_id"))
        if self.source_document_version is not None:
            object.__setattr__(
                self,
                "source_document_version",
                _text(self.source_document_version, "source_document_version"),
            )
        object.__setattr__(self, "source_hash_sha256", _text(self.source_hash_sha256, "source_hash_sha256"))


def duration_domain_dependency_matches(
    published: DurationDomainDependencyBinding,
    current: DurationDomainDependencyBinding,
) -> bool:
    if not isinstance(published, DurationDomainDependencyBinding) or not isinstance(
        current, DurationDomainDependencyBinding
    ):
        raise DurationDomainBindingError(
            "published and current must be DurationDomainDependencyBinding values"
        )
    return published == current


def _scope_identity(value: Mapping[str, object]) -> tuple[str, str | None]:
    raw_scope = value.get("scope_type", WaitingPeriodScopeType.POLICY_WIDE.value)
    try:
        scope_type = WaitingPeriodScopeType(str(raw_scope)).value
    except ValueError as exc:
        raise DurationDomainBindingError("scope_type is not supported by the ontology") from exc
    scope_reference = value.get("scope_reference")
    if scope_type == WaitingPeriodScopeType.BENEFIT_SCOPED.value:
        return scope_type, _text(scope_reference, "scope_reference")
    if scope_reference is not None:
        raise DurationDomainBindingError("POLICY_WIDE must not define scope_reference")
    return scope_type, None


def validate_duration_domain_reference(
    *,
    base_value: Mapping[str, object],
    base_applicability: ApplicabilityKey,
    base_ontology_version: str,
    reference: DurationDomainReference,
    domain_fact: SemanticFact,
) -> None:
    """Validate mapping/publication integrity for one base-mechanic → duration-domain edge."""
    if not isinstance(base_value, Mapping):
        raise DurationDomainBindingError("base_value must be a mapping")
    if not isinstance(base_applicability, ApplicabilityKey):
        raise DurationDomainBindingError("base_applicability must be ApplicabilityKey")
    base_ontology_version = _text(base_ontology_version, "base_ontology_version")
    if not isinstance(reference, DurationDomainReference):
        raise DurationDomainBindingError("reference must be DurationDomainReference")
    if not isinstance(domain_fact, SemanticFact):
        raise DurationDomainBindingError("domain_fact must be SemanticFact")

    try:
        base_type = WaitingPeriodType(str(base_value.get("waiting_period_type"))).value
    except ValueError as exc:
        raise DurationDomainBindingError(
            "base waiting_period_type is not supported by the ontology"
        ) from exc

    if reference.semantic_fact_id != domain_fact.fact_id:
        raise DurationDomainBindingError("duration-domain fact identity does not match reference")
    if reference.waiting_period_type != base_type:
        raise DurationDomainBindingError("duration-domain reference waiting-period type mismatch")
    if reference.ontology_version != base_ontology_version:
        raise DurationDomainBindingError("duration-domain reference ontology version mismatch")
    if domain_fact.semantic_type != "DURATION_SELECTION":
        raise DurationDomainBindingError("referenced fact must be DURATION_SELECTION")
    if domain_fact.ontology_version != base_ontology_version:
        raise DurationDomainBindingError("duration-domain fact ontology version mismatch")
    if domain_fact.applicability != base_applicability:
        raise DurationDomainBindingError("duration-domain fact applicability mismatch")
    if domain_fact.value.get("waiting_period_type") != base_type:
        raise DurationDomainBindingError("duration-domain fact waiting-period type mismatch")
    if domain_fact.value.get("value_source") != WaitingPeriodValueSource.POLICY_SCHEDULE_SELECTED.value:
        raise DurationDomainBindingError(
            "duration-domain fact must be POLICY_SCHEDULE_SELECTED"
        )
    options = domain_fact.value.get("duration_options")
    if not isinstance(options, (tuple, list)) or not options:
        raise DurationDomainBindingError("duration-domain fact must have non-empty duration_options")

    base_scope = _scope_identity(base_value)
    domain_scope = _scope_identity(domain_fact.value)
    if base_scope != domain_scope:
        raise DurationDomainBindingError("duration-domain fact scope identity mismatch")


__all__ = [
    "DurationDomainBindingError",
    "DurationDomainDependencyBinding",
    "DurationDomainReference",
    "duration_domain_dependency_matches",
    "validate_duration_domain_reference",
]
