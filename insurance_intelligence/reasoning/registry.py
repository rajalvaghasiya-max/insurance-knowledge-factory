"""Versioned deterministic registry for Reasoning Engine rules (MO-017B)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from insurance_intelligence.contracts.evidence import EVIDENCE_ROLES
from insurance_intelligence.contracts.reasoning import FINDING_TYPES
from insurance_intelligence.contracts.reasoning_plan import AUTHORITY_REQUIREMENTS, DOMAIN_VALUES

RULE_TOPICS = frozenset(
    {
        "any",
        "copay",
        "conditional_copayment",
        "coverage",
        "exclusion",
        "eligibility",
        "claim_condition",
        "documented_fact",
    }
)


class RuleRegistryError(ValueError):
    """Raised when rule metadata or registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise RuleRegistryError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise RuleRegistryError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ReasoningRuleDefinition:
    rule_id: str
    rule_version: str
    domain: str
    topic: str
    supported_requirement_types: tuple[str, ...]
    required_evidence_topics: tuple[str, ...]
    required_evidence_roles: tuple[str, ...]
    required_authority: str
    required_inputs: tuple[str, ...]
    output_finding_types: tuple[str, ...]
    execution_priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.rule_id, self.rule_version)


def build_rule_definition(
    *,
    rule_id: str,
    rule_version: str,
    domain: str,
    topic: str,
    supported_requirement_types: Sequence[str],
    required_evidence_topics: Sequence[str],
    required_evidence_roles: Sequence[str],
    required_authority: str,
    required_inputs: Sequence[str] = (),
    output_finding_types: Sequence[str],
    execution_priority: int = 100,
) -> ReasoningRuleDefinition:
    if isinstance(execution_priority, bool) or not isinstance(execution_priority, int) or execution_priority < 0:
        raise RuleRegistryError("execution_priority must be a non-negative integer")
    requirement_types = _unique(supported_requirement_types, "supported_requirement_types")
    evidence_topics = _unique(required_evidence_topics, "required_evidence_topics")
    evidence_roles = _unique(required_evidence_roles, "required_evidence_roles")
    finding_types = _unique(output_finding_types, "output_finding_types")
    if not requirement_types:
        raise RuleRegistryError("supported_requirement_types must not be empty")
    if not finding_types:
        raise RuleRegistryError("output_finding_types must not be empty")
    for role in evidence_roles:
        _member(role, EVIDENCE_ROLES, "required_evidence_roles[]")
    for finding_type in finding_types:
        _member(finding_type, FINDING_TYPES, "output_finding_types[]")
    return ReasoningRuleDefinition(
        rule_id=_text(rule_id, "rule_id"),
        rule_version=_text(rule_version, "rule_version"),
        domain=_member(domain, DOMAIN_VALUES, "domain"),
        topic=_member(topic, RULE_TOPICS, "topic"),
        supported_requirement_types=requirement_types,
        required_evidence_topics=evidence_topics,
        required_evidence_roles=evidence_roles,
        required_authority=_member(required_authority, AUTHORITY_REQUIREMENTS, "required_authority"),
        required_inputs=_unique(required_inputs, "required_inputs"),
        output_finding_types=finding_types,
        execution_priority=execution_priority,
    )


class ReasoningRuleRegistry:
    """Immutable-by-interface registry with deterministic lookup ordering."""

    def __init__(self, rules: Iterable[ReasoningRuleDefinition] = ()) -> None:
        self._rules: dict[tuple[str, str], ReasoningRuleDefinition] = {}
        self._rule_ids: set[str] = set()
        for rule in rules:
            self.register(rule)

    def register(self, rule: ReasoningRuleDefinition) -> None:
        if not isinstance(rule, ReasoningRuleDefinition):
            raise RuleRegistryError("rule must be a ReasoningRuleDefinition")
        if rule.registry_key in self._rules:
            raise RuleRegistryError(f"duplicate rule registration: {rule.rule_id}@{rule.rule_version}")
        if rule.rule_id in self._rule_ids:
            raise RuleRegistryError(f"ambiguous duplicate rule_id: {rule.rule_id}")
        self._rules[rule.registry_key] = rule
        self._rule_ids.add(rule.rule_id)

    def all_rules(self) -> tuple[ReasoningRuleDefinition, ...]:
        return tuple(sorted(self._rules.values(), key=self._sort_key))

    def get(self, rule_id: str, rule_version: str | None = None) -> ReasoningRuleDefinition:
        rid = _text(rule_id, "rule_id")
        if rule_version is None:
            matches = [rule for rule in self._rules.values() if rule.rule_id == rid]
            if len(matches) != 1:
                raise RuleRegistryError(f"rule_id not registered: {rid}")
            return matches[0]
        key = (rid, _text(rule_version, "rule_version"))
        try:
            return self._rules[key]
        except KeyError as exc:
            raise RuleRegistryError(f"rule not registered: {key[0]}@{key[1]}") from exc

    def eligible_rules(
        self,
        *,
        domain: str,
        topic: str,
        requirement_type: str,
        available_evidence_topics: Sequence[str] = (),
        available_evidence_roles: Sequence[str] = (),
        available_authorities: Sequence[str] = (),
        available_inputs: Sequence[str] = (),
    ) -> tuple[ReasoningRuleDefinition, ...]:
        validated_domain = _member(domain, DOMAIN_VALUES, "domain")
        validated_topic = _member(topic, RULE_TOPICS, "topic")
        requirement = _text(requirement_type, "requirement_type")
        topics = set(_unique(available_evidence_topics, "available_evidence_topics"))
        roles = set(_unique(available_evidence_roles, "available_evidence_roles"))
        authorities = set(_unique(available_authorities, "available_authorities"))
        inputs = set(_unique(available_inputs, "available_inputs"))
        matches = []
        for rule in self._rules.values():
            if rule.domain not in {validated_domain, "unknown"}:
                continue
            if rule.topic not in {validated_topic, "any"}:
                continue
            if requirement not in rule.supported_requirement_types:
                continue
            if not set(rule.required_evidence_topics).issubset(topics):
                continue
            if not set(rule.required_evidence_roles).issubset(roles):
                continue
            if rule.required_authority not in authorities and "ANY_GOVERNED" not in authorities:
                continue
            if not set(rule.required_inputs).issubset(inputs):
                continue
            matches.append(rule)
        return tuple(sorted(matches, key=self._sort_key))

    @staticmethod
    def _sort_key(rule: ReasoningRuleDefinition) -> tuple[int, str, str]:
        return (rule.execution_priority, rule.rule_id, rule.rule_version)
