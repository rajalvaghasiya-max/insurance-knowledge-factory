"""Generic deterministic assembler for evidence-backed conditional rules.

The assembler only combines already-normalized complete rule candidates. It does
not parse insurance language, infer missing conditions, or broaden scope. Domain
scope semantics are available only through an injected reconciliation policy.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable

from factory_core.rules.conditional_rule_fragment_models import (
    ConditionalRuleFragment,
    FragmentCompleteness,
    FragmentRole,
)
from factory_core.rules.conditional_rule_models import (
    ConditionalRule,
    EvidenceReference,
    RuleEvidence,
    RulePredicate,
)
from factory_core.rules.conditional_rule_reconciliation import (
    RuleCompatibilityKey,
    compatibility_key,
    evidence_priority_key,
    select_primary_and_corroborating,
)
from factory_core.rules.scope_reconciliation_policy import (
    ScopeReconciliationPolicy,
    ScopeRelation,
)


@dataclass(frozen=True, slots=True)
class ConditionalRuleAssemblyResult:
    """Output boundary preserving rules and non-published fragments separately."""

    assembled_rules: tuple[ConditionalRule, ...]
    unassembled_fragments: tuple[ConditionalRuleFragment, ...]


class ConditionalRuleAssembler:
    """Assemble complete fragments without interpreting domain terminology.

    With no scope policy, compatibility remains exact. A domain may inject a
    policy that canonicalizes its own hierarchy and permits a lower-authority
    empty scope to become corroboration of one uniquely compatible, more-specific
    evidence-backed rule. The core never treats partial scope as a new rule fact.
    """

    def __init__(self, *, scope_policy: ScopeReconciliationPolicy | None = None) -> None:
        self._scope_policy = scope_policy

    def assemble(self, fragments: Iterable[ConditionalRuleFragment]) -> ConditionalRuleAssemblyResult:
        candidates: list[ConditionalRuleFragment] = []
        unassembled: list[ConditionalRuleFragment] = []
        for fragment in fragments:
            if self._is_publishable_candidate(fragment):
                candidates.append(fragment)
            else:
                unassembled.append(fragment)

        if self._scope_policy is None:
            groups: dict[RuleCompatibilityKey, list[ConditionalRuleFragment]] = {}
            for fragment in candidates:
                groups.setdefault(compatibility_key(fragment), []).append(fragment)
            rules = [self._build_rule(key, group, group[0].coverage_scope) for key, group in groups.items()]
        else:
            rules = self._assemble_with_scope_policy(candidates)

        rules.sort(key=lambda rule: rule.rule_id)
        return ConditionalRuleAssemblyResult(
            assembled_rules=tuple(rules),
            unassembled_fragments=tuple(sorted(unassembled, key=lambda item: item.fragment_id)),
        )

    def _assemble_with_scope_policy(
        self,
        candidates: list[ConditionalRuleFragment],
    ) -> list[ConditionalRule]:
        """Group candidates after domain-owned canonicalization.

        The core joins only exact or policy-declared compatible-partial scopes.
        Compatible scopes are represented by the union of their explicit,
        normalized predicates. No predicate is invented by the Factory core.
        """
        assert self._scope_policy is not None
        base_groups: dict[tuple[object, ...], list[ConditionalRuleFragment]] = {}
        for fragment in candidates:
            key = compatibility_key(fragment)
            base = (key.concept_id, key.rule_type, key.effect, key.applies_when)
            base_groups.setdefault(base, []).append(fragment)

        rules: list[ConditionalRule] = []
        for fragments in base_groups.values():
            concrete_groups: list[tuple[tuple[RulePredicate, ...], list[ConditionalRuleFragment]]] = []
            empty_scope: list[ConditionalRuleFragment] = []

            for fragment in sorted(fragments, key=lambda item: evidence_priority_key(item.evidence)):
                normalized = self._scope_policy.normalize_scope(fragment.coverage_scope)
                if not normalized:
                    empty_scope.append(fragment)
                    continue
                matches = [
                    index for index, (scope, _) in enumerate(concrete_groups)
                    if self._scope_policy.relation(scope, normalized)
                    in (ScopeRelation.EXACT, ScopeRelation.COMPATIBLE_PARTIAL)
                ]
                if len(matches) == 1:
                    index = matches[0]
                    old_scope, members = concrete_groups[index]
                    concrete_groups[index] = (self._union_scope(old_scope, normalized), [*members, fragment])
                else:
                    concrete_groups.append((normalized, [fragment]))

            unresolved_empty: list[ConditionalRuleFragment] = []
            for partial in empty_scope:
                matches = [
                    index for index, (scope, members) in enumerate(concrete_groups)
                    if self._scope_policy.relation((), scope) is ScopeRelation.COMPATIBLE_PARTIAL
                    and self._highest_authority(members) > partial.evidence.authority_score
                ]
                if len(matches) == 1:
                    index = matches[0]
                    scope, members = concrete_groups[index]
                    concrete_groups[index] = (scope, [*members, partial])
                else:
                    unresolved_empty.append(partial)

            if unresolved_empty:
                concrete_groups.append(((), unresolved_empty))

            for scope, members in concrete_groups:
                primary = min(members, key=lambda item: evidence_priority_key(item.evidence))
                base_key = compatibility_key(primary)
                scope_key = tuple(sorted((item.dimension, item.operator.value, item.value) for item in scope))
                resolved_key = RuleCompatibilityKey(
                    concept_id=base_key.concept_id,
                    rule_type=base_key.rule_type,
                    effect=base_key.effect,
                    applies_when=base_key.applies_when,
                    coverage_scope=scope_key,
                )
                rules.append(self._build_rule(resolved_key, members, scope))
        return rules

    @staticmethod
    def _union_scope(
        left: tuple[RulePredicate, ...],
        right: tuple[RulePredicate, ...],
    ) -> tuple[RulePredicate, ...]:
        values = {(item.dimension, item.operator.value, item.value): item for item in (*left, *right)}
        return tuple(sorted(values.values(), key=lambda item: (item.dimension, item.operator.value, str(item.value))))

    @staticmethod
    def _highest_authority(fragments: list[ConditionalRuleFragment]) -> int:
        return max(item.evidence.authority_score for item in fragments)

    @staticmethod
    def _is_publishable_candidate(fragment: ConditionalRuleFragment) -> bool:
        return (
            fragment.role is FragmentRole.RULE_CANDIDATE
            and fragment.completeness is FragmentCompleteness.COMPLETE
            and fragment.effect is not None
            and not fragment.unresolved_ambiguities
        )

    @staticmethod
    def _build_rule(
        key: RuleCompatibilityKey,
        fragments: list[ConditionalRuleFragment],
        resolved_scope: tuple[RulePredicate, ...],
    ) -> ConditionalRule:
        primary, corroborating = select_primary_and_corroborating(fragments)
        corroborating_evidence = tuple(
            ConditionalRuleAssembler._as_corroborating_reference(item.evidence)
            for item in corroborating
        )
        assembly_key = ConditionalRuleAssembler._assembly_key(key)
        return ConditionalRule(
            rule_id=f"cr_{assembly_key[:16]}",
            concept_id=primary.concept_id,
            rule_type=primary.rule_type,
            effect=primary.effect,
            applies_when=tuple(sorted(primary.applies_when, key=lambda item: (item.dimension, item.operator.value, str(item.value)))),
            coverage_scope=tuple(sorted(resolved_scope, key=lambda item: (item.dimension, item.operator.value, str(item.value)))),
            evidence=RuleEvidence(primary=primary.evidence, corroborating=corroborating_evidence),
            assembly_key=assembly_key,
        )

    @staticmethod
    def _as_corroborating_reference(evidence: EvidenceReference) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=evidence.evidence_id,
            document_id=evidence.document_id,
            document_type=evidence.document_type,
            authority_score=evidence.authority_score,
            fragment_id=evidence.fragment_id,
            source_char_range=evidence.source_char_range,
            corroboration_role="corroborating",
        )

    @staticmethod
    def _assembly_key(key: RuleCompatibilityKey) -> str:
        payload = repr(key).encode("utf-8")
        return sha256(payload).hexdigest()
