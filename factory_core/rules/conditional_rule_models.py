"""Canonical, evidence-backed conditional rule contract.

This module deliberately contains no insurance-term, product, or Health-specific
logic. It represents only a rule's effect, applicability conditions, scope,
evidence lineage, authority, and unresolved ambiguity.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence


class RuleAssemblyStatus(StrEnum):
    EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED = "evidence_assembled_not_fact_extracted"
    BLOCKED_BY_AMBIGUITY = "blocked_by_ambiguity"


class ConditionOperator(StrEnum):
    EQUALS = "equals"
    IN = "in"
    NOT_EQUALS = "not_equals"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"


@dataclass(frozen=True, slots=True)
class RulePredicate:
    """A deterministic condition or scope predicate."""

    dimension: str
    operator: ConditionOperator
    value: str | int | float | bool | tuple[str | int | float | bool, ...]

    def __post_init__(self) -> None:
        if not self.dimension.strip():
            raise ValueError("RulePredicate.dimension must not be blank.")
        if self.operator is ConditionOperator.IN and not isinstance(self.value, tuple):
            raise ValueError("RulePredicate.value must be a tuple when operator='in'.")
        if self.operator is not ConditionOperator.IN and isinstance(self.value, tuple):
            raise ValueError("Tuple values are only valid when operator='in'.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["operator"] = self.operator.value
        if isinstance(self.value, tuple):
            result["value"] = list(self.value)
        return result


class RuleEffectValueKind(StrEnum):
    """How an evidenced effect value must be interpreted."""

    FIXED = "fixed"
    ALLOWED_SET = "allowed_set"


@dataclass(frozen=True, slots=True)
class RuleEffect:
    """The customer or policy effect created by a rule.

    A fixed value represents one deterministic outcome. An allowed set represents
    explicitly evidenced selectable values; it must not be flattened into one
    product-level value before policy-schedule or user-context evaluation.
    """

    operator: str
    value: int | float | str | bool | tuple[int | float | str | bool, ...] | None
    unit: str | None = None
    basis: str | None = None
    value_kind: RuleEffectValueKind = RuleEffectValueKind.FIXED

    def __post_init__(self) -> None:
        if not self.operator.strip():
            raise ValueError("RuleEffect.operator must not be blank.")
        if self.value is None:
            raise ValueError("RuleEffect.value must be explicitly known; use an unresolved ambiguity instead.")
        if self.value_kind is RuleEffectValueKind.FIXED and isinstance(self.value, tuple):
            raise ValueError("A fixed RuleEffect must use one scalar value, not a tuple.")
        if self.value_kind is RuleEffectValueKind.ALLOWED_SET:
            if not isinstance(self.value, tuple) or not self.value:
                raise ValueError("An allowed-set RuleEffect requires a non-empty tuple of explicit values.")
            if len(set(self.value)) != len(self.value):
                raise ValueError("An allowed-set RuleEffect cannot contain duplicate values.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["value_kind"] = self.value_kind.value
        if isinstance(self.value, tuple):
            result["value"] = list(self.value)
        return result


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """Immutable pointer to a primary or corroborating evidence fragment."""

    evidence_id: str
    document_id: str
    document_type: str
    authority_score: int
    fragment_id: str | None = None
    source_char_range: Mapping[str, int] | None = None
    corroboration_role: str | None = None

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.document_id.strip():
            raise ValueError("EvidenceReference requires non-blank evidence_id and document_id.")
        if self.authority_score < 0:
            raise ValueError("EvidenceReference.authority_score cannot be negative.")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        if self.source_char_range is not None:
            result["source_char_range"] = dict(self.source_char_range)
        return result


@dataclass(frozen=True, slots=True)
class RuleEvidence:
    primary: EvidenceReference
    corroborating: tuple[EvidenceReference, ...] = ()

    def __post_init__(self) -> None:
        duplicate_ids = [item.evidence_id for item in self.corroborating if item.evidence_id == self.primary.evidence_id]
        if duplicate_ids:
            raise ValueError("Primary evidence cannot also appear as corroborating evidence.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_evidence": self.primary.to_dict(),
            "corroborating_evidence": [item.to_dict() for item in self.corroborating],
        }


@dataclass(frozen=True, slots=True)
class ConditionalRule:
    """A non-flattened insurance rule assembled from explicit evidence."""

    rule_id: str
    concept_id: str
    rule_type: str
    effect: RuleEffect
    applies_when: tuple[RulePredicate, ...]
    coverage_scope: tuple[RulePredicate, ...]
    evidence: RuleEvidence
    status: RuleAssemblyStatus = RuleAssemblyStatus.EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED
    unresolved_ambiguities: tuple[str, ...] = ()
    assembly_key: str | None = None

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("ConditionalRule.rule_id must not be blank.")
        if not self.concept_id.strip():
            raise ValueError("ConditionalRule.concept_id must not be blank.")
        if not self.rule_type.strip():
            raise ValueError("ConditionalRule.rule_type must not be blank.")
        if self.status is RuleAssemblyStatus.EVIDENCE_ASSEMBLED_NOT_FACT_EXTRACTED and self.unresolved_ambiguities:
            raise ValueError(
                "Rules with unresolved ambiguities must use status='blocked_by_ambiguity'; "
                "the system must not silently publish a seemingly complete rule."
            )
        if self.status is RuleAssemblyStatus.BLOCKED_BY_AMBIGUITY and not self.unresolved_ambiguities:
            raise ValueError("Blocked rules require at least one unresolved ambiguity.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "concept_id": self.concept_id,
            "rule_type": self.rule_type,
            "effect": self.effect.to_dict(),
            "applies_when": [item.to_dict() for item in self.applies_when],
            "coverage_scope": [item.to_dict() for item in self.coverage_scope],
            "evidence": self.evidence.to_dict(),
            "status": self.status.value,
            "unresolved_ambiguities": list(self.unresolved_ambiguities),
            "assembly_key": self.assembly_key,
        }
