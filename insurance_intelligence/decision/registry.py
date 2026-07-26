"""Versioned deterministic registry for Decision and Safety Gate policies (MO-018B)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from insurance_intelligence.contracts.decision import (
    DECISION_OUTCOMES,
    FINDING_DISPOSITIONS,
    SAFETY_ISSUE_TYPES,
    SAFETY_SEVERITIES,
)
from insurance_intelligence.contracts.evidence import RESOLUTION_STATUSES, SUFFICIENCY_STATUSES
from insurance_intelligence.contracts.reasoning import (
    DERIVATION_TYPES,
    FINDING_STATUSES,
    FINDING_TYPES,
    REASONING_STATUSES,
    REASONING_SUFFICIENCY_STATUSES,
)

POLICY_DOMAINS = frozenset({"any", "health", "motor", "life", "travel", "unknown"})
POLICY_TOPICS = frozenset(
    {
        "any",
        "copay",
        "conditional_copayment",
        "coverage",
        "exclusion",
        "eligibility",
        "claim_condition",
        "recommendation",
        "documented_fact",
    }
)
STRICT_MODES = frozenset({"ANY", "STRICT", "PERMISSIVE"})


class SafetyPolicyRegistryError(ValueError):
    """Raised when safety-policy metadata or registry state is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SafetyPolicyRegistryError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise SafetyPolicyRegistryError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise SafetyPolicyRegistryError(f"{label} values must be unique")
    return result


def _validate_members(values: tuple[str, ...], allowed: frozenset[str], label: str) -> tuple[str, ...]:
    for value in values:
        _member(value, allowed, f"{label}[]")
    return values


@dataclass(frozen=True)
class SafetyPolicyDefinition:
    policy_id: str
    policy_version: str
    domain: str
    topic: str
    finding_types: tuple[str, ...]
    finding_statuses: tuple[str, ...]
    derivation_types: tuple[str, ...]
    reasoning_statuses: tuple[str, ...]
    reasoning_sufficiency_statuses: tuple[str, ...]
    evidence_resolution_statuses: tuple[str, ...]
    evidence_sufficiency_statuses: tuple[str, ...]
    strict_modes: tuple[str, ...]
    required_context_keys: tuple[str, ...]
    prohibited_operations: tuple[str, ...]
    issue_type: str
    severity: str
    finding_disposition: str
    decision_outcome: str
    blocking: bool
    evaluation_priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.policy_id, self.policy_version)


def build_policy_definition(
    *,
    policy_id: str,
    policy_version: str,
    domain: str,
    topic: str,
    issue_type: str,
    severity: str,
    finding_disposition: str,
    decision_outcome: str,
    finding_types: Sequence[str] = (),
    finding_statuses: Sequence[str] = (),
    derivation_types: Sequence[str] = (),
    reasoning_statuses: Sequence[str] = (),
    reasoning_sufficiency_statuses: Sequence[str] = (),
    evidence_resolution_statuses: Sequence[str] = (),
    evidence_sufficiency_statuses: Sequence[str] = (),
    strict_modes: Sequence[str] = ("ANY",),
    required_context_keys: Sequence[str] = (),
    prohibited_operations: Sequence[str] = (),
    blocking: bool = False,
    evaluation_priority: int = 100,
) -> SafetyPolicyDefinition:
    if not isinstance(blocking, bool):
        raise SafetyPolicyRegistryError("blocking must be boolean")
    if isinstance(evaluation_priority, bool) or not isinstance(evaluation_priority, int) or evaluation_priority < 0:
        raise SafetyPolicyRegistryError("evaluation_priority must be a non-negative integer")

    validated_modes = _validate_members(_unique(strict_modes, "strict_modes"), STRICT_MODES, "strict_modes")
    if not validated_modes:
        raise SafetyPolicyRegistryError("strict_modes must not be empty")
    if "ANY" in validated_modes and len(validated_modes) > 1:
        raise SafetyPolicyRegistryError("strict_modes cannot combine ANY with explicit modes")

    disposition = _member(finding_disposition, FINDING_DISPOSITIONS, "finding_disposition")
    outcome = _member(decision_outcome, DECISION_OUTCOMES, "decision_outcome")
    severity_value = _member(severity, SAFETY_SEVERITIES, "severity")
    if blocking and disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        raise SafetyPolicyRegistryError("blocking policies cannot approve findings")
    if blocking and outcome in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        raise SafetyPolicyRegistryError("blocking policies cannot produce approval outcomes")
    if severity_value == "CRITICAL" and not blocking:
        raise SafetyPolicyRegistryError("CRITICAL safety policies must be blocking")

    return SafetyPolicyDefinition(
        policy_id=_text(policy_id, "policy_id"),
        policy_version=_text(policy_version, "policy_version"),
        domain=_member(domain, POLICY_DOMAINS, "domain"),
        topic=_member(topic, POLICY_TOPICS, "topic"),
        finding_types=_validate_members(_unique(finding_types, "finding_types"), FINDING_TYPES, "finding_types"),
        finding_statuses=_validate_members(
            _unique(finding_statuses, "finding_statuses"), FINDING_STATUSES, "finding_statuses"
        ),
        derivation_types=_validate_members(
            _unique(derivation_types, "derivation_types"), DERIVATION_TYPES, "derivation_types"
        ),
        reasoning_statuses=_validate_members(
            _unique(reasoning_statuses, "reasoning_statuses"), REASONING_STATUSES, "reasoning_statuses"
        ),
        reasoning_sufficiency_statuses=_validate_members(
            _unique(reasoning_sufficiency_statuses, "reasoning_sufficiency_statuses"),
            REASONING_SUFFICIENCY_STATUSES,
            "reasoning_sufficiency_statuses",
        ),
        evidence_resolution_statuses=_validate_members(
            _unique(evidence_resolution_statuses, "evidence_resolution_statuses"),
            RESOLUTION_STATUSES,
            "evidence_resolution_statuses",
        ),
        evidence_sufficiency_statuses=_validate_members(
            _unique(evidence_sufficiency_statuses, "evidence_sufficiency_statuses"),
            SUFFICIENCY_STATUSES,
            "evidence_sufficiency_statuses",
        ),
        strict_modes=validated_modes,
        required_context_keys=_unique(required_context_keys, "required_context_keys"),
        prohibited_operations=_unique(prohibited_operations, "prohibited_operations"),
        issue_type=_member(issue_type, SAFETY_ISSUE_TYPES, "issue_type"),
        severity=severity_value,
        finding_disposition=disposition,
        decision_outcome=outcome,
        blocking=blocking,
        evaluation_priority=evaluation_priority,
    )


class SafetyPolicyRegistry:
    """Immutable-by-interface registry with deterministic fail-closed matching."""

    def __init__(self, policies: Iterable[SafetyPolicyDefinition] = ()) -> None:
        self._policies: dict[tuple[str, str], SafetyPolicyDefinition] = {}
        self._policy_ids: set[str] = set()
        for policy in policies:
            self.register(policy)

    def register(self, policy: SafetyPolicyDefinition) -> None:
        if not isinstance(policy, SafetyPolicyDefinition):
            raise SafetyPolicyRegistryError("policy must be a SafetyPolicyDefinition")
        if policy.registry_key in self._policies:
            raise SafetyPolicyRegistryError(
                f"duplicate policy registration: {policy.policy_id}@{policy.policy_version}"
            )
        if policy.policy_id in self._policy_ids:
            raise SafetyPolicyRegistryError(f"ambiguous duplicate policy_id: {policy.policy_id}")
        self._policies[policy.registry_key] = policy
        self._policy_ids.add(policy.policy_id)

    def all_policies(self) -> tuple[SafetyPolicyDefinition, ...]:
        return tuple(sorted(self._policies.values(), key=self._sort_key))

    def get(self, policy_id: str, policy_version: str | None = None) -> SafetyPolicyDefinition:
        pid = _text(policy_id, "policy_id")
        if policy_version is None:
            matches = [policy for policy in self._policies.values() if policy.policy_id == pid]
            if len(matches) != 1:
                raise SafetyPolicyRegistryError(f"policy_id not registered: {pid}")
            return matches[0]
        key = (pid, _text(policy_version, "policy_version"))
        try:
            return self._policies[key]
        except KeyError as exc:
            raise SafetyPolicyRegistryError(f"policy not registered: {key[0]}@{key[1]}") from exc

    def eligible_policies(
        self,
        *,
        domain: str,
        topic: str,
        finding_type: str,
        finding_status: str,
        derivation_type: str,
        reasoning_status: str,
        reasoning_sufficiency: str,
        evidence_resolution_status: str,
        evidence_sufficiency: str,
        strict_mode: str,
        available_context_keys: Sequence[str] = (),
        requested_operations: Sequence[str] = (),
    ) -> tuple[SafetyPolicyDefinition, ...]:
        validated_domain = _member(domain, POLICY_DOMAINS, "domain")
        validated_topic = _member(topic, POLICY_TOPICS, "topic")
        _member(finding_type, FINDING_TYPES, "finding_type")
        _member(finding_status, FINDING_STATUSES, "finding_status")
        _member(derivation_type, DERIVATION_TYPES, "derivation_type")
        _member(reasoning_status, REASONING_STATUSES, "reasoning_status")
        _member(reasoning_sufficiency, REASONING_SUFFICIENCY_STATUSES, "reasoning_sufficiency")
        _member(evidence_resolution_status, RESOLUTION_STATUSES, "evidence_resolution_status")
        _member(evidence_sufficiency, SUFFICIENCY_STATUSES, "evidence_sufficiency")
        _member(strict_mode, frozenset({"STRICT", "PERMISSIVE"}), "strict_mode")
        context_keys = set(_unique(available_context_keys, "available_context_keys"))
        operations = set(_unique(requested_operations, "requested_operations"))

        matches: list[SafetyPolicyDefinition] = []
        for policy in self._policies.values():
            if policy.domain not in {"any", validated_domain}:
                continue
            if policy.topic not in {"any", validated_topic}:
                continue
            if policy.finding_types and finding_type not in policy.finding_types:
                continue
            if policy.finding_statuses and finding_status not in policy.finding_statuses:
                continue
            if policy.derivation_types and derivation_type not in policy.derivation_types:
                continue
            if policy.reasoning_statuses and reasoning_status not in policy.reasoning_statuses:
                continue
            if policy.reasoning_sufficiency_statuses and reasoning_sufficiency not in policy.reasoning_sufficiency_statuses:
                continue
            if policy.evidence_resolution_statuses and evidence_resolution_status not in policy.evidence_resolution_statuses:
                continue
            if policy.evidence_sufficiency_statuses and evidence_sufficiency not in policy.evidence_sufficiency_statuses:
                continue
            if "ANY" not in policy.strict_modes and strict_mode not in policy.strict_modes:
                continue
            if not set(policy.required_context_keys).issubset(context_keys):
                continue
            if policy.prohibited_operations and not set(policy.prohibited_operations).intersection(operations):
                continue
            matches.append(policy)
        return tuple(sorted(matches, key=self._sort_key))

    @staticmethod
    def _sort_key(policy: SafetyPolicyDefinition) -> tuple[int, str, str]:
        return (policy.evaluation_priority, policy.policy_id, policy.policy_version)
