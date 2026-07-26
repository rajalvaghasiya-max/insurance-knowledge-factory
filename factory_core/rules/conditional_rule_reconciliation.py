"""Deterministic compatibility and authority policies for rule fragments.

This module is generic. It never interprets insurance terminology; it compares
already-normalized fragments exactly and orders evidence deterministically.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from factory_core.rules.conditional_rule_fragment_models import ConditionalRuleFragment
from factory_core.rules.conditional_rule_models import EvidenceReference, RuleEffect, RulePredicate


@dataclass(frozen=True, slots=True)
class RuleCompatibilityKey:
    """The full semantic identity required before fragments may be assembled."""

    concept_id: str
    rule_type: str
    effect: tuple[str, str, object, str | None, str | None]
    applies_when: tuple[tuple[str, str, object], ...]
    coverage_scope: tuple[tuple[str, str, object], ...]


def _canonical_value(value: object) -> object:
    return tuple(value) if isinstance(value, tuple) else value


def _predicate_key(predicates: tuple[RulePredicate, ...]) -> tuple[tuple[str, str, object], ...]:
    # Conditions are a set semantically, so input order must not affect identity.
    return tuple(sorted((item.dimension, item.operator.value, _canonical_value(item.value)) for item in predicates))


def _effect_key(effect: RuleEffect) -> tuple[str, str, object, str | None, str | None]:
    return (effect.operator, effect.value_kind.value, _canonical_value(effect.value), effect.unit, effect.basis)


def compatibility_key(fragment: ConditionalRuleFragment) -> RuleCompatibilityKey:
    """Return an exact, order-insensitive key for a complete rule candidate."""
    if fragment.effect is None:
        raise ValueError("Only fragments with an explicit effect have a compatibility key.")
    return RuleCompatibilityKey(
        concept_id=fragment.concept_id,
        rule_type=fragment.rule_type,
        effect=_effect_key(fragment.effect),
        applies_when=_predicate_key(fragment.applies_when),
        coverage_scope=_predicate_key(fragment.coverage_scope),
    )


def evidence_priority_key(evidence: EvidenceReference) -> tuple[int, str, str, str]:
    """Sort evidence deterministically: authority desc, then stable identifiers asc."""
    return (-evidence.authority_score, evidence.document_type, evidence.document_id, evidence.evidence_id)


def select_primary_and_corroborating(
    fragments: Iterable[ConditionalRuleFragment],
) -> tuple[ConditionalRuleFragment, tuple[ConditionalRuleFragment, ...]]:
    """Select one primary fragment and deduplicate corroboration by evidence id."""
    ordered = sorted(fragments, key=lambda item: evidence_priority_key(item.evidence))
    if not ordered:
        raise ValueError("At least one compatible fragment is required.")

    primary = ordered[0]
    seen = {primary.evidence.evidence_id}
    corroborating: list[ConditionalRuleFragment] = []
    for candidate in ordered[1:]:
        if candidate.evidence.evidence_id in seen:
            continue
        seen.add(candidate.evidence.evidence_id)
        corroborating.append(candidate)
    return primary, tuple(corroborating)
