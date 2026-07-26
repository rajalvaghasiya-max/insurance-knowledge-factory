"""Deterministic reasoning rules for MO-017C.

Rules consume already-governed evidence packages and approved context only. They do
not retrieve evidence, mutate inputs, calculate monetary outcomes, or generate
consumer-facing explanations.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Mapping, Sequence

from insurance_intelligence.contracts.evidence import EvidencePackage
from insurance_intelligence.contracts.reasoning import Finding, build_finding
from insurance_intelligence.reasoning.registry import (
    ReasoningRuleDefinition,
    ReasoningRuleRegistry,
    build_rule_definition,
)

RULE_VERSION = "1.0"
TRIGGER_STATUSES = frozenset({"CONFIRMED", "NOT_TRIGGERED", "UNRESOLVED"})


class ReasoningRuleError(ValueError):
    """Raised when deterministic rule inputs are invalid or unsupported."""


@dataclass(frozen=True)
class RuleInput:
    requirement_id: str
    evidence: tuple[EvidencePackage, ...]
    approved_context: Mapping[str, object]
    scope: str = "product"


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReasoningRuleError(f"{label} must be a non-empty string")
    return value.strip()


def build_rule_input(
    *,
    requirement_id: str,
    evidence: Sequence[EvidencePackage],
    approved_context: Mapping[str, object] | None = None,
    scope: str = "product",
) -> RuleInput:
    items = tuple(evidence)
    if not all(isinstance(item, EvidencePackage) for item in items):
        raise ReasoningRuleError("evidence must contain EvidencePackage values")
    identifiers = [item.evidence_id for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise ReasoningRuleError("evidence IDs must be unique")
    requirement = _nonempty(requirement_id, "requirement_id")
    if any(item.requirement_id != requirement for item in items):
        raise ReasoningRuleError("all evidence must match requirement_id")
    return RuleInput(requirement, items, dict(approved_context or {}), _nonempty(scope, "scope"))


def _stable_id(prefix: str, payload: Mapping[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(encoded).hexdigest()[:20]}"


def _usable(evidence: Sequence[EvidencePackage]) -> tuple[EvidencePackage, ...]:
    return tuple(
        sorted(
            (
                item
                for item in evidence
                if item.evidence_role not in {"CONTRADICTING", "SUPERSEDED", "INAPPLICABLE"}
                and item.lineage.lineage_status == "VERIFIED"
                and item.applicability_status in {"APPLICABLE", "POLICY_SPECIFIC_OVERRIDE"}
            ),
            key=lambda item: (item.authority_rank, item.evidence_id),
        )
    )


def _finding_id(rule_id: str, data: RuleInput, evidence_ids: Sequence[str], effect: str) -> str:
    return _stable_id(
        "finding",
        {
            "rule_id": rule_id,
            "requirement_id": data.requirement_id,
            "evidence_ids": tuple(evidence_ids),
            "effect": effect,
            "scope": data.scope,
        },
    )


def direct_documented_fact(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "direct_documented_fact_v1"
    findings = []
    for evidence in _usable(data.evidence):
        effect = evidence.claim.strip()
        findings.append(
            build_finding(
                finding_id=_finding_id(rule_id, data, (evidence.evidence_id,), effect),
                requirement_id=data.requirement_id,
                finding_type="DOCUMENTED_FACT",
                subject=evidence.governed_entity_reference,
                predicate="documents",
                object_or_effect=effect,
                condition=None,
                scope=data.scope,
                finding_status="SUPPORTED",
                derivation_type="DIRECT_FACT",
                rule_id=rule_id,
                rule_version=RULE_VERSION,
                evidence_ids=(evidence.evidence_id,),
                confidence=evidence.confidence,
            )
        )
    return tuple(findings)


_PERCENTAGE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%")


def _percentage(evidence: EvidencePackage) -> str:
    for text in (evidence.claim, evidence.source_excerpt or ""):
        match = _PERCENTAGE.search(text)
        if match:
            return f"{match.group(1)}%"
    raise ReasoningRuleError("conditional co-payment evidence must contain a documented percentage")

_TRIGGER_PATTERNS = (
    re.compile(r"(?:for\s+)?insured persons? whose age at the time of entry is [^.;]+", re.I),
    re.compile(r"(?:when|if|where|in case|provided that|subject to)\s+[^.;]+", re.I),
)
_EXCEPTION_PATTERNS = (
    re.compile(
        r"(?:this|the)\s+co-payment\s+"
        r"(?:does not apply|is not applicable|will not apply|shall not apply)\s+"
        r"(?:for|where|when|if)\s+[^.;]+",
        re.I,
    ),
    re.compile(
        r"(?:does not apply|is not applicable|will not apply|shall not apply)\s+"
        r"(?:for|where|when|if)\s+[^.;]+",
        re.I,
    ),
)
_SCOPE_PATTERNS = (
    re.compile(
        r"(?:the\s+policy\s+wording\s+)?limits\s+(?:this|the)\s+co-payment\s+to\s+.+?(?=\.\s+[A-Z]|;|$)",
        re.I,
    ),
    re.compile(
        r"(?:this|the)\s+co-payment\s+is\s+applicable\s+(?:only\s+)?(?:for|to)\s+.+?(?=\.\s+[A-Z]|;|$)",
        re.I,
    ),
    re.compile(r"(?:applicable\s+only\s+to|only\s+for)\s+.+?(?=\.\s+[A-Z]|;|$)", re.I),
)
_EXCEPTION_SIGNAL_PATTERNS = (
    re.compile(
        r"\bco-payment\b.{0,100}\b(?:does\s+not\s+apply|is\s+not\s+applicable|"
        r"will\s+not\s+apply|shall\s+not\s+apply|waived|exempt)\b",
        re.I,
    ),
)
_SCOPE_SIGNAL_PATTERNS = (
    re.compile(
        r"(?:\b(?:limits?|restricts?|confines?)\b.{0,80}\bco-payment\b.{0,30}\bto\b|"
        r"\bco-payment\b.{0,100}\b(?:applicable\s+only|limited\s+to|restricted\s+to|confined\s+to)\b)",
        re.I,
    ),
)


def _clean_clause(value: str) -> str:
    return " ".join(value.strip().rstrip(" .;").split())


def _first_clause(text: str, patterns: Sequence[re.Pattern[str]]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _clean_clause(match.group(0))
    return None


def _conditional_semantics(evidence: EvidencePackage) -> tuple[str, str | None, str | None]:
    text = " ".join((evidence.claim or evidence.source_excerpt or "").split())
    trigger = _first_clause(text, _TRIGGER_PATTERNS)
    exception = _first_clause(text, _EXCEPTION_PATTERNS)
    applicability_scope = _first_clause(text, _SCOPE_PATTERNS)
    if not trigger:
        raise ReasoningRuleError("conditional co-payment evidence must contain a documented trigger condition")
    if any(pattern.search(text) for pattern in _EXCEPTION_SIGNAL_PATTERNS) and not exception:
        raise ReasoningRuleError(
            "conditional co-payment evidence signals an exception that could not be extracted safely"
        )
    if any(pattern.search(text) for pattern in _SCOPE_SIGNAL_PATTERNS) and not applicability_scope:
        raise ReasoningRuleError(
            "conditional co-payment evidence signals applicability scope that could not be extracted safely"
        )
    return trigger, exception, applicability_scope


def _condition(evidence: EvidencePackage) -> str:
    """Backward-compatible trigger accessor without consuming later clauses."""
    return _conditional_semantics(evidence)[0]

def _copay_evidence(data: RuleInput) -> EvidencePackage:
    candidates = [
        item
        for item in _usable(data.evidence)
        if item.field_or_topic.lower() in {"copay", "co_payment", "co-payment", "conditional_copayment"}
        or "co-pay" in item.claim.lower()
        or "copay" in item.claim.lower()
        or "co-payment" in item.claim.lower()
    ]
    if not candidates:
        raise ReasoningRuleError("no usable conditional co-payment evidence")
    return sorted(candidates, key=lambda item: (item.authority_rank, item.evidence_id))[0]


def conditional_copayment_obligation(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_obligation_v1"
    evidence = _copay_evidence(data)
    percentage = _percentage(evidence)
    trigger, exception, applicability_scope = _conditional_semantics(evidence)
    effect = f"{percentage} of the admissible claim amount"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, (evidence.evidence_id,), effect),
        requirement_id=data.requirement_id,
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect=effect,
        condition=trigger,
        trigger=trigger,
        exception=exception,
        applicability_scope=applicability_scope,
        scope=data.scope,
        finding_status="CONDITIONAL",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        evidence_ids=(evidence.evidence_id,),
        confidence=min(evidence.confidence, 0.95),
    )
    return (finding,)


def conditional_copayment_nontriggered(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_nontriggered_v1"
    evidence = _copay_evidence(data)
    status = data.approved_context.get("conditional_copayment_trigger_status")
    if status != "NOT_TRIGGERED":
        raise ReasoningRuleError("approved trigger status NOT_TRIGGERED is required")
    trigger, exception, applicability_scope = _conditional_semantics(evidence)
    effect = "the documented conditional co-payment obligation is not triggered"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, (evidence.evidence_id,), effect),
        requirement_id=data.requirement_id,
        finding_type="CLAIM_CONDITION",
        subject="conditional co-payment obligation",
        predicate="is_not_triggered",
        object_or_effect=effect,
        condition=f"approved context establishes that {trigger} does not apply",
        trigger=trigger,
        exception=exception,
        applicability_scope=applicability_scope,
        scope=data.scope,
        finding_status="SUPPORTED",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        evidence_ids=(evidence.evidence_id,),
        confidence=min(evidence.confidence, 0.95),
    )
    return (finding,)


def conditional_copayment_trigger_unresolved(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_trigger_unresolved_v1"
    evidence = _copay_evidence(data)
    status = data.approved_context.get("conditional_copayment_trigger_status", "UNRESOLVED")
    if status not in {None, "UNRESOLVED"}:
        raise ReasoningRuleError("trigger-unresolved rule requires absent or UNRESOLVED trigger status")
    trigger, exception, applicability_scope = _conditional_semantics(evidence)
    effect = "case-specific applicability cannot be concluded from the approved context"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, (evidence.evidence_id,), effect),
        requirement_id=data.requirement_id,
        finding_type="UNRESOLVED_IMPLICATION",
        subject="conditional co-payment clause",
        predicate="requires_trigger_context",
        object_or_effect=effect,
        condition=trigger,
        trigger=trigger,
        exception=exception,
        applicability_scope=applicability_scope,
        scope=data.scope,
        finding_status="PARTIALLY_SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        evidence_ids=(evidence.evidence_id,),
        limitations=("The actual trigger state is not present in approved context.",),
        confidence=min(evidence.confidence, 0.8),
    )
    return (finding,)


def rule_definitions() -> tuple[ReasoningRuleDefinition, ...]:
    return (
        build_rule_definition(
            rule_id="direct_documented_fact_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="any",
            supported_requirement_types=("EXTRACT_FACTS", "EXPLAIN", "DERIVE_IMPLICATIONS"),
            required_evidence_topics=(),
            required_evidence_roles=("SUPPORTING",),
            required_authority="ANY_GOVERNED",
            output_finding_types=("DOCUMENTED_FACT",),
            execution_priority=10,
        ),
        build_rule_definition(
            rule_id="conditional_copayment_obligation_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="conditional_copayment",
            supported_requirement_types=("EXPLAIN", "DERIVE_IMPLICATIONS"),
            required_evidence_topics=("conditional_copayment",),
            required_evidence_roles=("SUPPORTING",),
            required_authority="AUTHORITATIVE",
            output_finding_types=("CLAIM_COST_SHARING",),
            execution_priority=20,
        ),
        build_rule_definition(
            rule_id="conditional_copayment_nontriggered_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="conditional_copayment",
            supported_requirement_types=("ASSESS_APPLICABILITY",),
            required_evidence_topics=("conditional_copayment",),
            required_evidence_roles=("SUPPORTING",),
            required_authority="AUTHORITATIVE",
            required_inputs=("conditional_copayment_trigger_status",),
            output_finding_types=("CLAIM_CONDITION",),
            execution_priority=30,
        ),
        build_rule_definition(
            rule_id="conditional_copayment_trigger_unresolved_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="conditional_copayment",
            supported_requirement_types=("ASSESS_APPLICABILITY",),
            required_evidence_topics=("conditional_copayment",),
            required_evidence_roles=("SUPPORTING",),
            required_authority="AUTHORITATIVE",
            output_finding_types=("UNRESOLVED_IMPLICATION",),
            execution_priority=40,
        ),
    )


def default_rule_registry() -> ReasoningRuleRegistry:
    return ReasoningRuleRegistry(rule_definitions())


def execute_rule(rule_id: str, data: RuleInput) -> tuple[Finding, ...]:
    executors = {
        "direct_documented_fact_v1": direct_documented_fact,
        "conditional_copayment_obligation_v1": conditional_copayment_obligation,
        "conditional_copayment_nontriggered_v1": conditional_copayment_nontriggered,
        "conditional_copayment_trigger_unresolved_v1": conditional_copayment_trigger_unresolved,
    }
    try:
        executor = executors[rule_id]
    except KeyError as exc:
        raise ReasoningRuleError(f"unregistered executable rule: {rule_id}") from exc
    return executor(data)
