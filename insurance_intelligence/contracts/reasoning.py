"""Executable contracts for the deterministic Reasoning Engine (MO-017)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan

SUPPORTED_CONTRACT_VERSION = "1.0"
STRICT_MODES = frozenset({"STRICT", "PERMISSIVE"})

FINDING_TYPES = frozenset(
    {
        "INSURANCE_OBLIGATION",
        "FINANCIAL_OBLIGATION",
        "COVERAGE_CONDITION",
        "COVERAGE_EFFECT",
        "CLAIM_CONDITION",
        "CLAIM_COST_SHARING",
        "ELIGIBILITY_CONDITION",
        "LIMITATION",
        "EXCLUSION_EFFECT",
        "DOCUMENTED_FACT",
        "UNRESOLVED_IMPLICATION",
    }
)
FINDING_STATUSES = frozenset(
    {
        "SUPPORTED",
        "SUPPORTED_WITH_LIMITATIONS",
        "CONDITIONAL",
        "PARTIALLY_SUPPORTED",
        "CONFLICTING",
        "UNSUPPORTED",
        "BLOCKED",
    }
)
DERIVATION_TYPES = frozenset(
    {
        "DIRECT_FACT",
        "DETERMINISTIC_DERIVATION",
        "CONDITIONAL_DERIVATION",
        "CALCULATION",
        "COMPARATIVE_DERIVATION",
        "ASSUMPTION_DEPENDENT",
    }
)
ASSUMPTION_APPROVAL_STATUSES = frozenset(
    {"APPROVED_INPUT", "SYSTEM_DEFAULT", "UNAPPROVED", "REJECTED"}
)
REQUIREMENT_REASONING_STATUSES = frozenset(
    {
        "SATISFIED",
        "SATISFIED_WITH_LIMITATIONS",
        "PARTIALLY_SATISFIED",
        "CONDITIONAL",
        "CONFLICTING",
        "UNSUPPORTED",
        "BLOCKED_BY_EVIDENCE",
        "BLOCKED_BY_CONTEXT",
        "NO_APPLICABLE_RULE",
    }
)
REASONING_SUFFICIENCY_STATUSES = frozenset(
    {"COMPLETE", "SUFFICIENT", "PARTIAL", "CONDITIONAL", "CONFLICTING", "UNSUPPORTED", "BLOCKED"}
)
REASONING_STATUSES = frozenset(
    {
        "REASONED",
        "REASONED_WITH_LIMITATIONS",
        "PARTIALLY_REASONED",
        "CONDITIONAL",
        "CONFLICTING",
        "NOT_REASONED",
        "OUT_OF_SCOPE",
        "NO_REASONING_REQUIRED",
        "INVALID_INPUT",
    }
)
RULE_EXECUTION_STATUSES = frozenset(
    {"EXECUTED", "EXECUTED_WITH_LIMITATIONS", "REJECTED", "BLOCKED", "SKIPPED"}
)
TRACE_EVENT_TYPES = frozenset(
    {
        "REASONING_STARTED",
        "REQUIREMENT_RECEIVED",
        "EVIDENCE_STATUS_CHECKED",
        "RULE_CANDIDATE_FOUND",
        "RULE_SELECTED",
        "RULE_REJECTED",
        "REQUIRED_INPUT_CHECKED",
        "ASSUMPTION_CHECKED",
        "RULE_EXECUTED",
        "FINDING_CREATED",
        "FINDING_BLOCKED",
        "SUFFICIENCY_EVALUATED",
        "REASONING_COMPLETED",
    }
)
MATERIALITY_VALUES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})


class ReasoningContractError(ValueError):
    """Raised when a Reasoning Engine contract is invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReasoningContractError(f"{label} must be a non-empty string")
    return value


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ReasoningContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_bounded_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReasoningContractError(f"{label} must be a number")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ReasoningContractError(f"{label} must be between 0 and 1; got {numeric}")
    return numeric


def _require_unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_require_nonempty_str(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise ReasoningContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ReasoningEngineInput:
    contract_version: str
    request_id: str
    reasoning_plan: ReasoningPlan
    evidence_resolution: EvidenceResolverOutput
    reasoning_context: Mapping[str, object]
    strict_mode: str


def build_input(
    *,
    request_id: str,
    reasoning_plan: ReasoningPlan,
    evidence_resolution: EvidenceResolverOutput,
    reasoning_context: Mapping[str, object] | None = None,
    strict_mode: str = "STRICT",
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> ReasoningEngineInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ReasoningContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(reasoning_plan, ReasoningPlan):
        raise ReasoningContractError("reasoning_plan must be a validated ReasoningPlan")
    if not isinstance(evidence_resolution, EvidenceResolverOutput):
        raise ReasoningContractError("evidence_resolution must be a validated EvidenceResolverOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if reasoning_plan.request_id != validated_request_id:
        raise ReasoningContractError("request_id must match reasoning_plan")
    if evidence_resolution.request_id != validated_request_id:
        raise ReasoningContractError("request_id must match evidence_resolution")
    return ReasoningEngineInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        reasoning_plan=reasoning_plan,
        evidence_resolution=evidence_resolution,
        reasoning_context=dict(reasoning_context or {}),
        strict_mode=_require_member(strict_mode, STRICT_MODES, "strict_mode"),
    )


@dataclass(frozen=True)
class Assumption:
    assumption_id: str
    description: str
    source: str
    approval_status: str
    used_by_finding_ids: tuple[str, ...]
    materiality: str


def build_assumption(
    *,
    assumption_id: str,
    description: str,
    source: str,
    approval_status: str,
    used_by_finding_ids: Sequence[str] = (),
    materiality: str = "MEDIUM",
) -> Assumption:
    return Assumption(
        assumption_id=_require_nonempty_str(assumption_id, "assumption_id"),
        description=_require_nonempty_str(description, "assumption.description"),
        source=_require_nonempty_str(source, "assumption.source"),
        approval_status=_require_member(approval_status, ASSUMPTION_APPROVAL_STATUSES, "assumption.approval_status"),
        used_by_finding_ids=_require_unique(used_by_finding_ids, "assumption.used_by_finding_ids"),
        materiality=_require_member(materiality, MATERIALITY_VALUES, "assumption.materiality"),
    )


@dataclass(frozen=True)
class Finding:
    finding_id: str
    requirement_id: str
    finding_type: str
    subject: str
    predicate: str
    object_or_effect: str
    condition: str | None
    scope: str
    finding_status: str
    derivation_type: str
    rule_id: str
    rule_version: str
    evidence_ids: tuple[str, ...]
    supporting_fact_ids: tuple[str, ...]
    assumption_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    confidence: float
    trigger: str | None = None
    exception: str | None = None
    applicability_scope: str | None = None


def build_finding(
    *,
    finding_id: str,
    requirement_id: str,
    finding_type: str,
    subject: str,
    predicate: str,
    object_or_effect: str,
    scope: str,
    finding_status: str,
    derivation_type: str,
    rule_id: str,
    rule_version: str,
    evidence_ids: Sequence[str],
    supporting_fact_ids: Sequence[str] = (),
    assumption_ids: Sequence[str] = (),
    limitations: Sequence[str] = (),
    condition: str | None = None,
    trigger: str | None = None,
    exception: str | None = None,
    applicability_scope: str | None = None,
    confidence: float = 1.0,
) -> Finding:
    if condition is not None:
        _require_nonempty_str(condition, "finding.condition")
    if trigger is not None:
        _require_nonempty_str(trigger, "finding.trigger")
    if exception is not None:
        _require_nonempty_str(exception, "finding.exception")
    if applicability_scope is not None:
        _require_nonempty_str(applicability_scope, "finding.applicability_scope")
    resolved_trigger = trigger if trigger is not None else condition
    validated_evidence = _require_unique(evidence_ids, "finding.evidence_ids")
    if finding_status in {"SUPPORTED", "SUPPORTED_WITH_LIMITATIONS", "CONDITIONAL", "PARTIALLY_SUPPORTED"} and not validated_evidence:
        raise ReasoningContractError("supported findings must reference at least one evidence_id")
    return Finding(
        finding_id=_require_nonempty_str(finding_id, "finding_id"),
        requirement_id=_require_nonempty_str(requirement_id, "finding.requirement_id"),
        finding_type=_require_member(finding_type, FINDING_TYPES, "finding.finding_type"),
        subject=_require_nonempty_str(subject, "finding.subject"),
        predicate=_require_nonempty_str(predicate, "finding.predicate"),
        object_or_effect=_require_nonempty_str(object_or_effect, "finding.object_or_effect"),
        condition=condition if condition is not None else resolved_trigger,
        trigger=resolved_trigger,
        exception=exception,
        applicability_scope=applicability_scope,
        scope=_require_nonempty_str(scope, "finding.scope"),
        finding_status=_require_member(finding_status, FINDING_STATUSES, "finding.finding_status"),
        derivation_type=_require_member(derivation_type, DERIVATION_TYPES, "finding.derivation_type"),
        rule_id=_require_nonempty_str(rule_id, "finding.rule_id"),
        rule_version=_require_nonempty_str(rule_version, "finding.rule_version"),
        evidence_ids=validated_evidence,
        supporting_fact_ids=_require_unique(supporting_fact_ids, "finding.supporting_fact_ids"),
        assumption_ids=_require_unique(assumption_ids, "finding.assumption_ids"),
        limitations=tuple(str(value) for value in limitations),
        confidence=_require_bounded_float(confidence, "finding.confidence"),
    )


@dataclass(frozen=True)
class RequirementReasoningResult:
    requirement_id: str
    status: str
    executed_rule_ids: tuple[str, ...]
    finding_ids: tuple[str, ...]
    rejected_rule_ids: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    unsupported_reason: str | None
    evidence_satisfied: bool
    context_satisfied: bool
    conflict_status: str
    confidence: float


def build_requirement_result(
    *,
    requirement_id: str,
    status: str,
    executed_rule_ids: Sequence[str] = (),
    finding_ids: Sequence[str] = (),
    rejected_rule_ids: Sequence[str] = (),
    missing_inputs: Sequence[str] = (),
    unsupported_reason: str | None = None,
    evidence_satisfied: bool,
    context_satisfied: bool,
    conflict_status: str,
    confidence: float,
) -> RequirementReasoningResult:
    if unsupported_reason is not None:
        _require_nonempty_str(unsupported_reason, "requirement_result.unsupported_reason")
    if not isinstance(evidence_satisfied, bool) or not isinstance(context_satisfied, bool):
        raise ReasoningContractError("requirement_result satisfaction flags must be boolean")
    return RequirementReasoningResult(
        requirement_id=_require_nonempty_str(requirement_id, "requirement_result.requirement_id"),
        status=_require_member(status, REQUIREMENT_REASONING_STATUSES, "requirement_result.status"),
        executed_rule_ids=_require_unique(executed_rule_ids, "requirement_result.executed_rule_ids"),
        finding_ids=_require_unique(finding_ids, "requirement_result.finding_ids"),
        rejected_rule_ids=_require_unique(rejected_rule_ids, "requirement_result.rejected_rule_ids"),
        missing_inputs=_require_unique(missing_inputs, "requirement_result.missing_inputs"),
        unsupported_reason=unsupported_reason,
        evidence_satisfied=evidence_satisfied,
        context_satisfied=context_satisfied,
        conflict_status=_require_nonempty_str(conflict_status, "requirement_result.conflict_status"),
        confidence=_require_bounded_float(confidence, "requirement_result.confidence"),
    )


@dataclass(frozen=True)
class RuleExecution:
    execution_id: str
    requirement_id: str
    rule_id: str
    rule_version: str
    status: str
    evidence_ids: tuple[str, ...]
    input_keys: tuple[str, ...]
    output_finding_ids: tuple[str, ...]
    rejection_reason: str | None
    confidence: float


def build_rule_execution(
    *,
    execution_id: str,
    requirement_id: str,
    rule_id: str,
    rule_version: str,
    status: str,
    evidence_ids: Sequence[str] = (),
    input_keys: Sequence[str] = (),
    output_finding_ids: Sequence[str] = (),
    rejection_reason: str | None = None,
    confidence: float = 0.0,
) -> RuleExecution:
    if rejection_reason is not None:
        _require_nonempty_str(rejection_reason, "rule_execution.rejection_reason")
    return RuleExecution(
        execution_id=_require_nonempty_str(execution_id, "rule_execution.execution_id"),
        requirement_id=_require_nonempty_str(requirement_id, "rule_execution.requirement_id"),
        rule_id=_require_nonempty_str(rule_id, "rule_execution.rule_id"),
        rule_version=_require_nonempty_str(rule_version, "rule_execution.rule_version"),
        status=_require_member(status, RULE_EXECUTION_STATUSES, "rule_execution.status"),
        evidence_ids=_require_unique(evidence_ids, "rule_execution.evidence_ids"),
        input_keys=_require_unique(input_keys, "rule_execution.input_keys"),
        output_finding_ids=_require_unique(output_finding_ids, "rule_execution.output_finding_ids"),
        rejection_reason=rejection_reason,
        confidence=_require_bounded_float(confidence, "rule_execution.confidence"),
    )


@dataclass(frozen=True)
class ReasoningTraceEvent:
    trace_id: str
    sequence: int
    event_type: str
    requirement_id: str | None
    rule_id: str | None
    evidence_ids: tuple[str, ...]
    decision: str
    basis: str
    input_references: tuple[str, ...]
    output_finding_ids: tuple[str, ...]
    order_marker: str


def build_trace_event(
    *,
    trace_id: str,
    sequence: int,
    event_type: str,
    decision: str,
    basis: str,
    order_marker: str,
    requirement_id: str | None = None,
    rule_id: str | None = None,
    evidence_ids: Sequence[str] = (),
    input_references: Sequence[str] = (),
    output_finding_ids: Sequence[str] = (),
) -> ReasoningTraceEvent:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ReasoningContractError("trace.sequence must be a positive integer")
    if requirement_id is not None:
        _require_nonempty_str(requirement_id, "trace.requirement_id")
    if rule_id is not None:
        _require_nonempty_str(rule_id, "trace.rule_id")
    return ReasoningTraceEvent(
        trace_id=_require_nonempty_str(trace_id, "trace.trace_id"),
        sequence=sequence,
        event_type=_require_member(event_type, TRACE_EVENT_TYPES, "trace.event_type"),
        requirement_id=requirement_id,
        rule_id=rule_id,
        evidence_ids=_require_unique(evidence_ids, "trace.evidence_ids"),
        decision=_require_nonempty_str(decision, "trace.decision"),
        basis=_require_nonempty_str(basis, "trace.basis"),
        input_references=_require_unique(input_references, "trace.input_references"),
        output_finding_ids=_require_unique(output_finding_ids, "trace.output_finding_ids"),
        order_marker=_require_nonempty_str(order_marker, "trace.order_marker"),
    )


@dataclass(frozen=True)
class ReasoningEngineOutput:
    contract_version: str
    request_id: str
    reasoning_id: str
    findings: tuple[Finding, ...]
    requirement_results: tuple[RequirementReasoningResult, ...]
    rule_executions: tuple[RuleExecution, ...]
    unsupported_requirements: tuple[str, ...]
    assumptions: tuple[Assumption, ...]
    limitations: tuple[str, ...]
    reasoning_sufficiency: str
    reasoning_status: str
    confidence: float
    reasoning_trace: tuple[ReasoningTraceEvent, ...]


def build_output(
    *,
    request_id: str,
    reasoning_id: str,
    findings: Sequence[Finding] = (),
    requirement_results: Sequence[RequirementReasoningResult] = (),
    rule_executions: Sequence[RuleExecution] = (),
    unsupported_requirements: Sequence[str] = (),
    assumptions: Sequence[Assumption] = (),
    limitations: Sequence[str] = (),
    reasoning_sufficiency: str,
    reasoning_status: str,
    confidence: float,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
    reasoning_trace: Sequence[ReasoningTraceEvent] = (),
) -> ReasoningEngineOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ReasoningContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")

    result = ReasoningEngineOutput(
        contract_version=contract_version,
        request_id=_require_nonempty_str(request_id, "request_id"),
        reasoning_id=_require_nonempty_str(reasoning_id, "reasoning_id"),
        findings=tuple(findings),
        requirement_results=tuple(requirement_results),
        rule_executions=tuple(rule_executions),
        unsupported_requirements=_require_unique(unsupported_requirements, "unsupported_requirements"),
        assumptions=tuple(assumptions),
        limitations=tuple(str(value) for value in limitations),
        reasoning_sufficiency=_require_member(
            reasoning_sufficiency, REASONING_SUFFICIENCY_STATUSES, "reasoning_sufficiency"
        ),
        reasoning_status=_require_member(reasoning_status, REASONING_STATUSES, "reasoning_status"),
        confidence=_require_bounded_float(confidence, "confidence"),
        reasoning_trace=tuple(reasoning_trace),
    )
    return validate_output(result)


def validate_output(output: ReasoningEngineOutput) -> ReasoningEngineOutput:
    if not isinstance(output, ReasoningEngineOutput):
        raise ReasoningContractError("output must be a ReasoningEngineOutput")
    if output.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ReasoningContractError("unsupported output contract_version")

    finding_ids = [finding.finding_id for finding in output.findings]
    if len(finding_ids) != len(set(finding_ids)):
        raise ReasoningContractError("finding_id values must be unique")
    requirement_ids = [result.requirement_id for result in output.requirement_results]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise ReasoningContractError("requirement result IDs must be unique")
    assumption_ids = [assumption.assumption_id for assumption in output.assumptions]
    if len(assumption_ids) != len(set(assumption_ids)):
        raise ReasoningContractError("assumption_id values must be unique")
    execution_ids = [execution.execution_id for execution in output.rule_executions]
    if len(execution_ids) != len(set(execution_ids)):
        raise ReasoningContractError("rule execution IDs must be unique")

    known_findings = set(finding_ids)
    known_requirements = set(requirement_ids)
    known_assumptions = set(assumption_ids)

    for finding in output.findings:
        if finding.requirement_id not in known_requirements:
            raise ReasoningContractError("finding references unknown requirement")
        if not set(finding.supporting_fact_ids) <= known_findings:
            raise ReasoningContractError("finding references unknown supporting fact")
        if not set(finding.assumption_ids) <= known_assumptions:
            raise ReasoningContractError("finding references unknown assumption")
        if finding.finding_id in finding.supporting_fact_ids:
            raise ReasoningContractError("finding cannot support itself")

    for result in output.requirement_results:
        if not set(result.finding_ids) <= known_findings:
            raise ReasoningContractError("requirement result references unknown finding")

    for execution in output.rule_executions:
        if execution.requirement_id not in known_requirements:
            raise ReasoningContractError("rule execution references unknown requirement")
        if not set(execution.output_finding_ids) <= known_findings:
            raise ReasoningContractError("rule execution references unknown finding")

    for assumption in output.assumptions:
        if not set(assumption.used_by_finding_ids) <= known_findings:
            raise ReasoningContractError("assumption references unknown finding")
        if assumption.approval_status in {"UNAPPROVED", "REJECTED"} and assumption.used_by_finding_ids:
            raise ReasoningContractError("unapproved or rejected assumptions cannot be used by findings")

    trace_sequences = [event.sequence for event in output.reasoning_trace]
    if trace_sequences != sorted(trace_sequences) or len(trace_sequences) != len(set(trace_sequences)):
        raise ReasoningContractError("reasoning trace sequence values must be unique and ordered")
    for event in output.reasoning_trace:
        if event.requirement_id is not None and event.requirement_id not in known_requirements:
            raise ReasoningContractError("trace references unknown requirement")
        if not set(event.output_finding_ids) <= known_findings:
            raise ReasoningContractError("trace references unknown finding")

    return output
