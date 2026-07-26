"""Domain-injected scope reconciliation contracts.

The Factory core never embeds insurance vocabulary. A domain policy may normalize
its own scopes and report whether two normalized scopes are exact, hierarchical,
partially compatible, disjoint, or unknown.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from factory_core.rules.conditional_rule_models import RulePredicate


class ScopeRelation(StrEnum):
    EXACT = "exact"
    BROADER_THAN = "broader_than"
    NARROWER_THAN = "narrower_than"
    COMPATIBLE_PARTIAL = "compatible_partial"
    DISJOINT = "disjoint"
    UNKNOWN = "unknown"


class ScopeReconciliationPolicy(Protocol):
    """A domain-owned semantic policy injected into generic assembly.

    ``normalize_scope`` may enrich an explicit scope only using deterministic,
    domain-maintained hierarchy data. It must not infer customer choices or
    policy facts absent from the evidence.
    """

    def normalize_scope(
        self,
        scope: tuple[RulePredicate, ...],
    ) -> tuple[RulePredicate, ...]:
        """Return a deterministic, canonical representation of one scope."""

    def relation(
        self,
        left: tuple[RulePredicate, ...],
        right: tuple[RulePredicate, ...],
    ) -> ScopeRelation:
        """Describe the semantic relation between two already-normalized scopes."""
