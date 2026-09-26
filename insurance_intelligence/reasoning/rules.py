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

from insurance_intelligence.benefits.copayment_composition import (
    CopaymentCompositionType,
    resolve_copayment_composition,
)
from insurance_intelligence.contracts.evidence import EvidencePackage
from insurance_intelligence.contracts.reasoning import (
    RULE_REJECTION_KINDS,
    Finding,
    build_finding,
)
from insurance_intelligence.contracts.semantic import build_governed_semantic_attribute
from insurance_intelligence.reasoning.registry import (
    ReasoningRuleDefinition,
    ReasoningRuleRegistry,
    build_rule_definition,
)
from insurance_intelligence.reasoning.waiting_period_applicability import (
    WaitingPeriodApplicabilityError,
    resolve_timeline,
)

RULE_VERSION = "1.0"
TRIGGER_STATUSES = frozenset({"CONFIRMED", "NOT_TRIGGERED", "UNRESOLVED"})


class ReasoningRuleError(ValueError):
    """Raised when deterministic rule inputs are invalid or unsupported."""

    def __init__(
        self,
        message: str,
        *,
        rejection_kind: str = "UNSUPPORTED_REASONING",
    ) -> None:
        if rejection_kind not in RULE_REJECTION_KINDS:
            raise ValueError(f"unsupported rejection_kind: {rejection_kind!r}")
        super().__init__(message)
        self.rejection_kind = rejection_kind


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
                semantic_attributes=evidence.semantic_attributes,
                confidence=evidence.confidence,
            )
        )
    return tuple(findings)


_PERCENTAGE = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%")


def _percentages(evidence: EvidencePackage) -> tuple[str, ...]:
    """Return documented co-payment percentages without collapsing option sets."""
    for text in (evidence.claim, evidence.source_excerpt or ""):
        matches = _PERCENTAGE.findall(text)
        if matches:
            ordered: list[str] = []
            for value in matches:
                percentage = f"{value}%"
                if percentage not in ordered:
                    ordered.append(percentage)
            return tuple(ordered)
    raise ReasoningRuleError("conditional co-payment evidence must contain a documented percentage")


def _clean_clause(value: str) -> str:
    return " ".join(value.strip().rstrip(" .;").split())


def _first_clause(text: str, patterns: Sequence[re.Pattern[str]]) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _clean_clause(match.group(0))
    return None


def _copayment_effect(evidence: EvidencePackage) -> str:
    percentages = _percentages(evidence)
    if len(percentages) == 1:
        effect = f"{percentages[0]} of the admissible claim amount"
    else:
        joined = ", ".join(percentages[:-1]) + f", or {percentages[-1]}"
        effect = (
            f"one of {joined} of the admissible claim amount, "
            "depending on the documented selected co-payment option"
        )
    text = " ".join((evidence.claim or evidence.source_excerpt or "").split())
    composition = resolve_copayment_composition(text)
    if composition.composition_type is not CopaymentCompositionType.STANDALONE:
        effect = f"{effect}; {composition.source_phrase}"
    return effect


_TRIGGER_BOUNDARY = r"(?=\s+(?:unless|except)\b|[.;]|$)"
_TRIGGER_PATTERNS = (
    re.compile(r"(?:when|if|where|in case|provided that|subject to)\s+[^,.;]+(?=,)", re.I),
    re.compile(
        rf"(?:for\s+)?insured persons? whose age at the time of entry is .+?{_TRIGGER_BOUNDARY}",
        re.I,
    ),
    re.compile(
        rf"(?:when|if|where|in case|provided that|subject to)\s+.+?{_TRIGGER_BOUNDARY}",
        re.I,
    ),
    re.compile(r"^for\s+[^,]+", re.I),
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
    re.compile(r"\bunless\s+.+?(?=[.;]|$)", re.I),
    re.compile(r"\bexcept(?:\s+(?:where|when|if|for))?\s+.+?(?=[.;]|$)", re.I),
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
    re.compile(r"^for\s+[^,]+", re.I),
    re.compile(r"(?:an|a|the)\s+in-?patient[^,.;]*claim\s+is\s+admitted", re.I),
)
_EXCEPTION_SIGNAL_PATTERNS = (
    re.compile(
        r"\bco-payment\b.{0,100}\b(?:does\s+not\s+apply|is\s+not\s+applicable|"
        r"will\s+not\s+apply|shall\s+not\s+apply|waived|exempt)\b",
        re.I,
    ),
    re.compile(r"\b(?:unless|except)\b", re.I),
)
_SCOPE_SIGNAL_PATTERNS = (
    re.compile(
        r"(?:\b(?:limits?|restricts?|confines?)\b.{0,80}\bco-payment\b.{0,30}\bto\b|"
        r"\bco-payment\b.{0,100}\b(?:applicable\s+only|limited\s+to|restricted\s+to|confined\s+to)\b)",
        re.I,
    ),
)


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
    selected = sorted(candidates, key=lambda item: (item.authority_rank, item.evidence_id))[0]
    if not selected.claim.strip():
        raise ReasoningRuleError(
            "governed conditional co-payment evidence must contain a non-empty reviewed claim"
        )
    return selected


_STRUCTURED_COPAY_KEYS = frozenset(
    {"rate", "trigger_condition", "exception_condition", "applicability_scope"}
)


def _structured_copay_semantics(
    data: RuleInput,
) -> tuple[str, str, str | None, str | None, tuple[str, ...], float] | None:
    values: dict[str, str] = {}
    evidence_ids: list[str] = []
    confidence = 1.0
    found = False
    for evidence in _usable(data.evidence):
        for attribute in evidence.semantic_attributes:
            if attribute.key not in _STRUCTURED_COPAY_KEYS:
                continue
            found = True
            value = _nonempty(attribute.value, f"semantic attribute {attribute.key}")
            existing = values.get(attribute.key)
            if existing is not None and existing != value:
                raise ReasoningRuleError(
                    f"conflicting structured co-payment semantic attribute: {attribute.key}"
                )
            values[attribute.key] = value
            if evidence.evidence_id not in evidence_ids:
                evidence_ids.append(evidence.evidence_id)
            confidence = min(confidence, evidence.confidence)
    if not found:
        return None
    missing = tuple(key for key in ("rate", "trigger_condition") if key not in values)
    if missing:
        raise ReasoningRuleError(
            "structured co-payment semantics are incomplete: missing " + ", ".join(missing)
        )
    return (
        values["rate"],
        values["trigger_condition"],
        values.get("exception_condition"),
        values.get("applicability_scope"),
        tuple(evidence_ids),
        confidence,
    )


def _copay_semantics(
    data: RuleInput,
) -> tuple[str, str, str | None, str | None, tuple[str, ...], float]:
    structured = _structured_copay_semantics(data)
    if structured is not None:
        return structured
    evidence = _copay_evidence(data)
    trigger, exception, applicability_scope = _conditional_semantics(evidence)
    effect = _copayment_effect(evidence)
    return (
        effect,
        trigger,
        exception,
        applicability_scope,
        (evidence.evidence_id,),
        evidence.confidence,
    )


def conditional_copayment_obligation(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_obligation_v1"
    effect, trigger, exception, applicability_scope, evidence_ids, confidence = _copay_semantics(data)
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, evidence_ids, effect),
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
        evidence_ids=evidence_ids,
        confidence=min(confidence, 0.95),
    )
    return (finding,)


def conditional_copayment_nontriggered(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_nontriggered_v1"
    status = data.approved_context.get("conditional_copayment_trigger_status")
    if status != "NOT_TRIGGERED":
        raise ReasoningRuleError("approved trigger status NOT_TRIGGERED is required")
    _, trigger, exception, applicability_scope, evidence_ids, confidence = _copay_semantics(data)
    effect = "the documented conditional co-payment obligation is not triggered"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, evidence_ids, effect),
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
        evidence_ids=evidence_ids,
        confidence=min(confidence, 0.95),
    )
    return (finding,)


def conditional_copayment_trigger_unresolved(data: RuleInput) -> tuple[Finding, ...]:
    rule_id = "conditional_copayment_trigger_unresolved_v1"
    status = data.approved_context.get("conditional_copayment_trigger_status", "UNRESOLVED")
    if status not in {None, "UNRESOLVED"}:
        raise ReasoningRuleError("trigger-unresolved rule requires absent or UNRESOLVED trigger status")
    _, trigger, exception, applicability_scope, evidence_ids, confidence = _copay_semantics(data)
    effect = "case-specific applicability cannot be concluded from the approved context"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, evidence_ids, effect),
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
        evidence_ids=evidence_ids,
        limitations=("The actual trigger state is not present in approved context.",),
        confidence=min(confidence, 0.8),
    )
    return (finding,)


_WAITING_PERIOD_REQUIRED_COMPONENTS = (
    "WAITING_PERIOD_DURATION",
    "WAITING_PERIOD_SUBJECT",
    "WAITING_PERIOD_START_BASIS",
)
_WAITING_PERIOD_OPTIONAL_COMPONENTS = (
    "APPLICABILITY_SCOPE",
    "CONTINUITY_OR_CREDIT_RULE",
    "EXCEPTION_CONDITION",
)
_WAITING_PERIOD_RESOLVED_CONTEXT_KEYS = (
    "policy_start_date",
    "claim_date",
    "waiting_period_continuity_credit_status",
    "waiting_period_exception_status",
)


def _waiting_period_components(data: RuleInput) -> dict[str, EvidencePackage]:
    selected: dict[str, EvidencePackage] = {}
    for evidence in _usable(data.evidence):
        component = evidence.field_or_topic.strip().upper()
        if component not in {*_WAITING_PERIOD_REQUIRED_COMPONENTS, *_WAITING_PERIOD_OPTIONAL_COMPONENTS}:
            continue
        existing = selected.get(component)
        if existing is not None and existing.claim.strip() != evidence.claim.strip():
            raise ReasoningRuleError(f"conflicting governed waiting-period component: {component}")
        selected[component] = evidence
    missing = tuple(component for component in _WAITING_PERIOD_REQUIRED_COMPONENTS if component not in selected)
    if missing:
        raise ReasoningRuleError(
            "governed waiting-period semantics are incomplete: missing " + ", ".join(missing)
        )
    return selected


def _resolved_waiting_period_context_present(data: RuleInput) -> bool:
    return all(key in data.approved_context for key in _WAITING_PERIOD_RESOLVED_CONTEXT_KEYS)


def waiting_period_applicability_resolved(data: RuleInput) -> tuple[Finding, ...]:
    """Resolve waiting-period timeline state from governed evidence and approved case facts."""
    rule_id = "waiting_period_applicability_resolved_v1"
    if not _resolved_waiting_period_context_present(data):
        raise ReasoningRuleError("resolved waiting-period case context is required")
    if data.approved_context.get("waiting_period_continuity_credit_status") != "NOT_APPLICABLE":
        raise ReasoningRuleError("continuity-credit status NOT_APPLICABLE is required for resolved timeline assessment")
    if data.approved_context.get("waiting_period_exception_status") != "NOT_APPLICABLE":
        raise ReasoningRuleError("waiting-period exception status NOT_APPLICABLE is required for resolved timeline assessment")

    components = _waiting_period_components(data)
    duration = components["WAITING_PERIOD_DURATION"].claim.strip()
    subject = components["WAITING_PERIOD_SUBJECT"].claim.strip()
    start_basis = components["WAITING_PERIOD_START_BASIS"].claim.strip()
    scope = components.get("APPLICABILITY_SCOPE")
    continuity = components.get("CONTINUITY_OR_CREDIT_RULE")
    exception = components.get("EXCEPTION_CONDITION")
    evidence = tuple(components.values())
    evidence_ids = tuple(sorted(item.evidence_id for item in evidence))
    confidence = min(item.confidence for item in evidence)

    try:
        timeline = resolve_timeline(
            start_date=data.approved_context["policy_start_date"],
            event_date=data.approved_context["claim_date"],
            duration_text=duration,
        )
    except WaitingPeriodApplicabilityError as exc:
        raise ReasoningRuleError(str(exc)) from exc
    if timeline.status == "BOUNDARY_UNRESOLVED":
        raise ReasoningRuleError(
            "waiting-period activation convention is unresolved at the calculated boundary date",
            rejection_kind="SOURCE_DOES_NOT_ESTABLISH",
        )

    if timeline.status == "NOT_COMPLETE":
        predicate = "is_still_active"
        effect = "the waiting period is still active on the approved claim date and is not complete"
    else:
        predicate = "is_complete"
        effect = "the waiting period is complete on the approved claim date"

    qualification_bits = []
    if continuity is not None:
        qualification_bits.append(continuity.claim.strip())
    if exception is not None:
        qualification_bits.append(exception.claim.strip())
    condition = (
        f"{duration} {start_basis} Approved policy start date: {timeline.start_date.isoformat()}; "
        f"approved claim date: {timeline.event_date.isoformat()}; calculated boundary date: "
        f"{timeline.boundary_date.isoformat()}."
    )
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, evidence_ids, effect),
        requirement_id=data.requirement_id,
        finding_type="CLAIM_CONDITION",
        subject="waiting period clause",
        predicate=predicate,
        object_or_effect=effect,
        condition=condition,
        trigger=condition,
        exception=" ".join(qualification_bits) or None,
        applicability_scope=scope.claim.strip() if scope is not None else subject,
        scope=data.scope,
        finding_status="SUPPORTED",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        evidence_ids=evidence_ids,
        limitations=(
            "This resolves only the governed waiting-period timeline state; it does not establish final claim approval or payment.",
        ),
        semantic_attributes=(
            build_governed_semantic_attribute(
                key="customer_qualification",
                value=(
                    "This resolves only the governed waiting-period timeline state; "
                    "it does not establish final claim approval or payment."
                ),
                evidence_references=evidence_ids,
            ),
        ),
        confidence=min(confidence, 0.95),
    )
    return (finding,)


def waiting_period_applicability_unresolved(data: RuleInput) -> tuple[Finding, ...]:
    """Expose governed waiting-period conditions without inventing customer facts."""
    rule_id = "waiting_period_applicability_unresolved_v1"
    if _resolved_waiting_period_context_present(data):
        raise ReasoningRuleError("resolved waiting-period case context is present")
    components = _waiting_period_components(data)
    duration = components["WAITING_PERIOD_DURATION"].claim.strip()
    subject = components["WAITING_PERIOD_SUBJECT"].claim.strip()
    start_basis = components["WAITING_PERIOD_START_BASIS"].claim.strip()
    scope = components.get("APPLICABILITY_SCOPE")
    continuity = components.get("CONTINUITY_OR_CREDIT_RULE")
    exception = components.get("EXCEPTION_CONDITION")
    evidence = tuple(components.values())
    evidence_ids = tuple(sorted(item.evidence_id for item in evidence))
    confidence = min(item.confidence for item in evidence)
    condition = " ".join((duration, start_basis))
    qualification_bits = [subject]
    if continuity is not None:
        qualification_bits.append(continuity.claim.strip())
    if exception is not None:
        qualification_bits.append(exception.claim.strip())
    effect = "case-specific waiting-period applicability requires additional approved context"
    finding = build_finding(
        finding_id=_finding_id(rule_id, data, evidence_ids, effect),
        requirement_id=data.requirement_id,
        finding_type="UNRESOLVED_IMPLICATION",
        subject="waiting period clause",
        predicate="requires_case_context",
        object_or_effect=effect,
        condition=condition,
        trigger=condition,
        exception=" ".join(qualification_bits[1:]) or None,
        applicability_scope=scope.claim.strip() if scope is not None else subject,
        scope=data.scope,
        finding_status="PARTIALLY_SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        evidence_ids=evidence_ids,
        limitations=(
            "The approved context does not establish elapsed waiting-period time, continuity credit, or exception applicability.",
        ),
        confidence=min(confidence, 0.8),
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
            rule_id="waiting_period_applicability_resolved_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="waiting_period",
            supported_requirement_types=("ASSESS_APPLICABILITY",),
            required_evidence_topics=("waiting_period",),
            required_evidence_roles=("SUPPORTING",),
            required_authority="AUTHORITATIVE",
            required_inputs=_WAITING_PERIOD_RESOLVED_CONTEXT_KEYS,
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
        build_rule_definition(
            rule_id="waiting_period_applicability_unresolved_v1",
            rule_version=RULE_VERSION,
            domain="health",
            topic="waiting_period",
            supported_requirement_types=("ASSESS_APPLICABILITY",),
            required_evidence_topics=("waiting_period",),
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
        "waiting_period_applicability_resolved_v1": waiting_period_applicability_resolved,
        "waiting_period_applicability_unresolved_v1": waiting_period_applicability_unresolved,
    }
    try:
        executor = executors[rule_id]
    except KeyError as exc:
        raise ReasoningRuleError(f"unregistered executable rule: {rule_id}") from exc
    return executor(data)
