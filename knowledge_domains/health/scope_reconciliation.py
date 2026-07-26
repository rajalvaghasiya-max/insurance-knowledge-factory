"""Health-domain scope normalization and relation policy.

This module owns Health vocabulary and hierarchy. The generic Factory core only
uses the policy interface; it never contains terms such as international care.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factory_core.rules.conditional_rule_models import ConditionOperator, RulePredicate
from factory_core.rules.scope_reconciliation_policy import ScopeRelation


@dataclass(frozen=True, slots=True)
class HealthScopeHierarchy:
    """Validated, deterministic Health scope hierarchy loaded from JSON."""

    scope_terms: dict[str, dict[str, Any]]

    @classmethod
    def from_file(cls, path: str | Path) -> "HealthScopeHierarchy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("domain") != "health":
            raise ValueError("Health scope hierarchy must declare domain='health'.")
        terms = payload.get("scope_terms")
        if not isinstance(terms, dict):
            raise ValueError("Health scope hierarchy requires object scope_terms.")
        return cls(scope_terms={str(key): value for key, value in terms.items() if isinstance(value, dict)})

    def canonical_term_for_scope_label(self, label: str) -> str | None:
        if label in self.scope_terms:
            return label
        for canonical, details in self.scope_terms.items():
            if label in {str(value) for value in details.get("aliases") or ()}:
                return canonical
        return None

    def parents_of(self, term: str) -> tuple[str, ...]:
        details = self.scope_terms.get(term) or {}
        return tuple(str(value) for value in details.get("parents") or ())

    def inferred_cover_for(self, term: str) -> str | None:
        value = (self.scope_terms.get(term) or {}).get("inferred_health_cover")
        return str(value) if value else None


class HealthScopeReconciliationPolicy:
    """Domain policy for exact, hierarchical and evidence-safe partial scopes."""

    def __init__(self, hierarchy: HealthScopeHierarchy | None = None) -> None:
        self._hierarchy = hierarchy or HealthScopeHierarchy.from_file(self._default_hierarchy_path())

    @staticmethod
    def _default_hierarchy_path() -> Path:
        return Path(__file__).resolve().parent / "rule_profiles" / "health_scope_hierarchy.json"

    def normalize_scope(self, scope: tuple[RulePredicate, ...]) -> tuple[RulePredicate, ...]:
        """Canonicalize aliases and enrich only proven Health cover hierarchy.

        A local scope label such as ``international_emergency_care_only`` is
        preserved verbatim for evidence fidelity. Its canonical hierarchy term
        may deterministically supply the more precise ``health_cover`` label.
        Any broader cover already present is removed only when the child scope
        explicitly establishes that it is too broad.
        """
        scope_labels = {
            str(item.value)
            for item in scope
            if item.dimension == "health_scope" and item.operator is ConditionOperator.EQUALS
        }
        canonical_terms = {
            canonical
            for label in scope_labels
            if (canonical := self._hierarchy.canonical_term_for_scope_label(label)) is not None
        }

        inferred_covers = {
            cover
            for term in canonical_terms
            if (cover := self._hierarchy.inferred_cover_for(term)) is not None
        }
        broad_parents = {
            parent
            for term in canonical_terms
            for parent in self._hierarchy.parents_of(term)
        }

        result: list[RulePredicate] = []
        for item in scope:
            if (
                item.dimension == "health_cover"
                and item.operator is ConditionOperator.EQUALS
                and str(item.value) in broad_parents
                and inferred_covers
            ):
                # The local scope proves a narrower cover. Replace an explicitly
                # broader cover, but never add a cover that the fragment did not
                # itself state; group-level reconciliation may later preserve a
                # compatible peer's explicit child cover.
                result.append(
                    RulePredicate(
                        "health_cover",
                        ConditionOperator.EQUALS,
                        sorted(inferred_covers)[0],
                    )
                )
                continue
            result.append(item)

        return tuple(sorted(result, key=lambda item: (item.dimension, item.operator.value, str(item.value))))

    def relation(
        self,
        left: tuple[RulePredicate, ...],
        right: tuple[RulePredicate, ...],
    ) -> ScopeRelation:
        if left == right:
            return ScopeRelation.EXACT
        if not left or not right:
            return ScopeRelation.COMPATIBLE_PARTIAL
        left_values = {(item.dimension, item.operator.value, item.value) for item in left}
        right_values = {(item.dimension, item.operator.value, item.value) for item in right}
        if left_values < right_values or right_values < left_values:
            return ScopeRelation.COMPATIBLE_PARTIAL
        return ScopeRelation.UNKNOWN
