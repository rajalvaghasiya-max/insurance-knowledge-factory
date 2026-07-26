"""Health-owned review policy for scenario-facing rule scope semantics.

A published conditional rule may contain predicates that are needed to decide
whether a concrete scenario matches, and labels that merely describe how the
rule was assembled or categorized.  This module makes that distinction explicit
without changing the generic evaluator or rewriting published rules.

Unknown predicates are deliberately returned as UNREVIEWED.  They must not be
silently treated as scenario inputs or metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from factory_core.rules.conditional_rule_models import ConditionalRule, RulePredicate


class ScenarioPredicateRole(StrEnum):
    """How a declared predicate is allowed to participate in scenario evaluation."""

    SCENARIO_REQUIRED = "scenario_required"
    RULE_METADATA_ONLY = "rule_metadata_only"
    DERIVABLE_FROM_OTHER_FACTS = "derivable_from_other_facts"
    UNREVIEWED = "unreviewed"


@dataclass(frozen=True, slots=True)
class PredicateSemanticsAssessment:
    """A reviewed classification for one predicate.

    ``DERIVABLE_FROM_OTHER_FACTS`` is descriptive at this stage.  No derivation
    is implemented here; a later domain normalizer must define and test it.
    """

    dimension: str
    value: str | int | float | bool | tuple[str | int | float | bool, ...]
    role: ScenarioPredicateRole
    reason: str


@dataclass(frozen=True, slots=True)
class RuleScenarioSemanticsReview:
    """Review output for one authoritative conditional rule."""

    rule_id: str
    applies_when: tuple[PredicateSemanticsAssessment, ...]
    coverage_scope: tuple[PredicateSemanticsAssessment, ...]

    @property
    def has_unreviewed_predicates(self) -> bool:
        return any(
            item.role is ScenarioPredicateRole.UNREVIEWED
            for item in (*self.applies_when, *self.coverage_scope)
        )

    @property
    def scenario_required_dimensions(self) -> tuple[str, ...]:
        dimensions = {
            item.dimension
            for item in (*self.applies_when, *self.coverage_scope)
            if item.role is ScenarioPredicateRole.SCENARIO_REQUIRED
        }
        return tuple(sorted(dimensions))


# Domain-owned, explicit taxonomy.  It is intentionally small and has no fuzzy
# matching.  New entries require domain review and tests.
_SCENARIO_REQUIRED_SCOPE_VALUES = {
    ("health_cover", "doctor_prescribed_investigations_cover"),
    ("health_cover", "doctor_consultation_cover"),
    ("health_cover", "international_emergency_care"),
    ("health_scope", "international_emergency_care_only"),
}

_METADATA_ONLY_SCOPE_VALUES = {
    ("health_scope", "claim_mode_specific"),
    ("health_scope", "voluntary_option"),
}


def classify_health_scope_predicate(predicate: RulePredicate) -> PredicateSemanticsAssessment:
    """Classify one Health coverage-scope predicate conservatively."""
    key = (predicate.dimension, predicate.value)
    if key in _SCENARIO_REQUIRED_SCOPE_VALUES:
        return PredicateSemanticsAssessment(
            dimension=predicate.dimension,
            value=predicate.value,
            role=ScenarioPredicateRole.SCENARIO_REQUIRED,
            reason="This predicate identifies a real claim or cover circumstance that must be supplied by a reviewed scenario boundary.",
        )
    if key in _METADATA_ONLY_SCOPE_VALUES:
        return PredicateSemanticsAssessment(
            dimension=predicate.dimension,
            value=predicate.value,
            role=ScenarioPredicateRole.RULE_METADATA_ONLY,
            reason="This label categorizes the published rule; it is not a standalone scenario fact and must not be requested or inferred from a user.",
        )
    return PredicateSemanticsAssessment(
        dimension=predicate.dimension,
        value=predicate.value,
        role=ScenarioPredicateRole.UNREVIEWED,
        reason="No reviewed Health scenario-semantic classification exists for this scope predicate.",
    )


def review_health_rule_scenario_semantics(rule: ConditionalRule) -> RuleScenarioSemanticsReview:
    """Review which predicates of a Health rule are scenario-facing.

    ``applies_when`` predicates are scenario-required by contract.  Scope
    predicates are classified through the Health-owned taxonomy above.
    """
    applies_when = tuple(
        PredicateSemanticsAssessment(
            dimension=predicate.dimension,
            value=predicate.value,
            role=ScenarioPredicateRole.SCENARIO_REQUIRED,
            reason="Rule applicability condition; a normalized scenario fact is required for deterministic evaluation.",
        )
        for predicate in rule.applies_when
    )
    coverage_scope = tuple(classify_health_scope_predicate(predicate) for predicate in rule.coverage_scope)
    return RuleScenarioSemanticsReview(
        rule_id=rule.rule_id,
        applies_when=applies_when,
        coverage_scope=coverage_scope,
    )
