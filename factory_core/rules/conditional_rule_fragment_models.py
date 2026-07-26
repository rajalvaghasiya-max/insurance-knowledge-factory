"""Structured, evidence-backed fragments for conditional insurance rules.

A fragment is an intermediate assertion extracted from one evidence location. It is
not a product-level fact and it is not an assembled rule. The generic assembler
may combine only compatible fragments while preserving every evidence pointer.

This module deliberately contains no term-, product-, insurer-, or Health-specific
logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from factory_core.rules.conditional_rule_models import (
    EvidenceReference,
    RuleEffect,
    RulePredicate,
)


class FragmentRole(StrEnum):
    """The contribution an evidence fragment can make to a later rule assembly."""

    RULE_CANDIDATE = "rule_candidate"
    SUPPORTING_DEFINITION = "supporting_definition"
    EXCEPTION_OR_LIMIT = "exception_or_limit"
    UNRESOLVED = "unresolved"


class FragmentCompleteness(StrEnum):
    """Explicitly describes what the parser knows, rather than guessing."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    SUPPORT_ONLY = "support_only"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True, slots=True)
class FragmentProvenance:
    """Reproducibility metadata for a deterministic parser result."""

    parser_id: str
    parser_version: str
    field_profile_id: str | None = None

    def __post_init__(self) -> None:
        if not self.parser_id.strip():
            raise ValueError("FragmentProvenance.parser_id must not be blank.")
        if not self.parser_version.strip():
            raise ValueError("FragmentProvenance.parser_version must not be blank.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConditionalRuleFragment:
    """A non-flattened contribution from exactly one evidence fragment.

    `effect` can be absent only when the fragment is support-only, partial, or
    unresolved. A complete rule candidate must have an explicit effect. This
    preserves the rule that unknown is safer than invented.
    """

    fragment_id: str
    concept_id: str
    rule_type: str
    role: FragmentRole
    completeness: FragmentCompleteness
    evidence: EvidenceReference
    provenance: FragmentProvenance
    effect: RuleEffect | None = None
    applies_when: tuple[RulePredicate, ...] = ()
    coverage_scope: tuple[RulePredicate, ...] = ()
    assembly_group_hint: str | None = None
    unresolved_ambiguities: tuple[str, ...] = ()
    source_text_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.fragment_id.strip():
            raise ValueError("ConditionalRuleFragment.fragment_id must not be blank.")
        if not self.concept_id.strip():
            raise ValueError("ConditionalRuleFragment.concept_id must not be blank.")
        if not self.rule_type.strip():
            raise ValueError("ConditionalRuleFragment.rule_type must not be blank.")
        if self.completeness is FragmentCompleteness.COMPLETE and self.effect is None:
            raise ValueError("A complete fragment requires an explicit effect.")
        if self.completeness is FragmentCompleteness.AMBIGUOUS and not self.unresolved_ambiguities:
            raise ValueError("An ambiguous fragment requires at least one unresolved ambiguity.")
        if self.completeness is not FragmentCompleteness.AMBIGUOUS and self.unresolved_ambiguities:
            raise ValueError(
                "Unresolved ambiguities require completeness='ambiguous'; do not silently publish uncertainty."
            )
        if self.role is FragmentRole.SUPPORTING_DEFINITION and self.effect is not None:
            raise ValueError("A supporting definition cannot assert a rule effect.")
        if self.role is FragmentRole.UNRESOLVED and self.completeness is not FragmentCompleteness.AMBIGUOUS:
            raise ValueError("An unresolved fragment must use completeness='ambiguous'.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "fragment_id": self.fragment_id,
            "concept_id": self.concept_id,
            "rule_type": self.rule_type,
            "role": self.role.value,
            "completeness": self.completeness.value,
            "effect": self.effect.to_dict() if self.effect else None,
            "applies_when": [predicate.to_dict() for predicate in self.applies_when],
            "coverage_scope": [predicate.to_dict() for predicate in self.coverage_scope],
            "evidence": self.evidence.to_dict(),
            "provenance": self.provenance.to_dict(),
            "assembly_group_hint": self.assembly_group_hint,
            "unresolved_ambiguities": list(self.unresolved_ambiguities),
            "source_text_hash": self.source_text_hash,
        }
