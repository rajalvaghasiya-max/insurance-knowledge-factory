"""Executable contracts for the deterministic Decision and Safety Gate (MO-018)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from insurance_intelligence.contracts.evidence import EvidenceResolverOutput
from insurance_intelligence.contracts.reasoning import Finding, ReasoningEngineOutput
from insurance_intelligence.contracts.reasoning_plan import ReasoningPlan

SUPPORTED_CONTRACT_VERSION = "1.0"
STRICT_MODES = frozenset({"STRICT", "PERMISSIVE"})
DECISION_OUTCOMES = frozenset(
    {
        "APPROVED",
        "APPROVED_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED",
        "INSUFFICIENT_EVIDENCE",
        "INSUFFICIENT_CONTEXT",
        "CONFLICTING_EVIDENCE",
        "UNSUPPORTED_REASONING",
        "HUMAN_REVIEW_REQUIRED",
        "BLOCKED",
        "OUT_OF_SCOPE",
    }
)
FINDING_DISPOSITIONS = frozenset(
    {
        "APPROVED",
        "APPROVED_WITH_LIMITATIONS",
        "WITHHELD_FOR_CLARIFICATION",
        "WITHHELD_INSUFFICIENT_EVIDENCE",
        "WITHHELD_INSUFFICIENT_CONTEXT",
        "WITHHELD_CONFLICT",
        "WITHHELD_UNSUPPORTED",
        "REFERRED_FOR_HUMAN_REVIEW",
        "BLOCKED",
    }
)
SAFETY_ISSUE_TYPES = frozenset(
    {
        "MISSING_EVIDENCE",
        "FAILED_LINEAGE",
        "VERSION_UNRESOLVED",
        "ENTITY_UNRESOLVED",
        "MATERIAL_CONFLICT",
        "MISSING_CONTEXT",
        "UNAPPROVED_ASSUMPTION",
        "UNSUPPORTED_INFERENCE",
        "RECOMMENDATION_WITHOUT_SUITABILITY",
        "OVERCONFIDENT_CONCLUSION",
        "OUT_OF_SCOPE_CONTENT",
        "POLICY_SPECIFIC_UNCERTAINTY",
        "HUMAN_REVIEW_TRIGGER",
    }
)
SAFETY_SEVERITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
ISSUE_STATUSES = frozenset({"OPEN", "MITIGATED", "WAIVED", "REFERRED", "BLOCKING"})
CLARIFICATION_PRIORITIES = frozenset({"LOW", "MEDIUM", "HIGH", "CRITICAL"})
CLARIFICATION_STATUSES = frozenset({"REQUIRED", "OPTIONAL", "RESOLVED", "WAIVED"})
BLOCK_REASONS = frozenset(
    {
        "FAILED_LINEAGE",
        "INSUFFICIENT_EVIDENCE",
        "INSUFFICIENT_CONTEXT",
        "CONFLICTING_EVIDENCE",
        "UNSUPPORTED_REASONING",
        "UNAPPROVED_ASSUMPTION",
        "OUT_OF_SCOPE",
        "HUMAN_REVIEW_REQUIRED",
        "SAFETY_POLICY",
    }
)
TRACE_EVENT_TYPES = frozenset(
    {
        "DECISION_STARTED",
        "INPUT_VALIDATED",
        "FINDING_RECEIVED",
        "SAFETY_POLICY_EVALUATED",
        "SAFETY_ISSUE_RECORDED",
        "FINDING_APPROVED",
        "FINDING_WITHHELD",
        "CLARIFICATION_REQUIRED",
        "HUMAN_REVIEW_REQUIRED",
        "RESPONSE_PACKET_ASSEMBLED",
        "DECISION_COMPLETED",
    }
)


class DecisionContractError(ValueError):
    """Raised when a Decision and Safety Gate contract is invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionContractError(f"{label} must be a non-empty string")
    return value


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise DecisionContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_bounded_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DecisionContractError(f"{label} must be a number")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise DecisionContractError(f"{label} must be between 0 and 1; got {numeric}")
    return numeric


def _require_unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_require_nonempty_str(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise DecisionContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class DecisionGateInput:
    contract_version: str
    request_id: str
    reasoning_plan: ReasoningPlan
    evidence_resolution: EvidenceResolverOutput
    reasoning_output: ReasoningEngineOutput
    decision_context: Mapping[str, object]
    strict_mode: str


def build_input(
    *,
    request_id: str,
    reasoning_plan: ReasoningPlan,
    evidence_resolution: EvidenceResolverOutput,
    reasoning_output: ReasoningEngineOutput,
    decision_context: Mapping[str, object] | None = None,
    strict_mode: str = "STRICT",
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> DecisionGateInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise DecisionContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(reasoning_plan, ReasoningPlan):
        raise DecisionContractError("reasoning_plan must be a validated ReasoningPlan")
    if not isinstance(evidence_resolution, EvidenceResolverOutput):
        raise DecisionContractError("evidence_resolution must be a validated EvidenceResolverOutput")
    if not isinstance(reasoning_output, ReasoningEngineOutput):
        raise DecisionContractError("reasoning_output must be a validated ReasoningEngineOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if reasoning_plan.request_id != validated_request_id:
        raise DecisionContractError("request_id must match reasoning_plan")
    if evidence_resolution.request_id != validated_request_id:
        raise DecisionContractError("request_id must match evidence_resolution")
    if reasoning_output.request_id != validated_request_id:
        raise DecisionContractError("request_id must match reasoning_output")
    return DecisionGateInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        reasoning_plan=reasoning_plan,
        evidence_resolution=evidence_resolution,
        reasoning_output=reasoning_output,
        decision_context=dict(decision_context or {}),
        strict_mode=_require_member(strict_mode, STRICT_MODES, "strict_mode"),
    )


@dataclass(frozen=True)
class FindingDisposition:
    finding_id: str
    disposition: str
    approved_evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    safety_issue_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]
    basis: str
    confidence: float


def build_finding_disposition(
    *,
    finding_id: str,
    disposition: str,
    basis: str,
    approved_evidence_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    safety_issue_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
    confidence: float = 0.0,
) -> FindingDisposition:
    validated_disposition = _require_member(disposition, FINDING_DISPOSITIONS, "finding_disposition.disposition")
    approved_evidence = _require_unique(approved_evidence_ids, "finding_disposition.approved_evidence_ids")
    if validated_disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} and not approved_evidence:
        raise DecisionContractError("approved finding dispositions must preserve approved evidence IDs")
    return FindingDisposition(
        finding_id=_require_nonempty_str(finding_id, "finding_disposition.finding_id"),
        disposition=validated_disposition,
        approved_evidence_ids=approved_evidence,
        limitation_ids=_require_unique(limitation_ids, "finding_disposition.limitation_ids"),
        safety_issue_ids=_require_unique(safety_issue_ids, "finding_disposition.safety_issue_ids"),
        clarification_ids=_require_unique(clarification_ids, "finding_disposition.clarification_ids"),
        basis=_require_nonempty_str(basis, "finding_disposition.basis"),
        confidence=_require_bounded_float(confidence, "finding_disposition.confidence"),
    )


@dataclass(frozen=True)
class SafetyIssue:
    issue_id: str
    issue_type: str
    severity: str
    status: str
    finding_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    description: str
    policy_id: str
    blocking: bool


def build_safety_issue(
    *,
    issue_id: str,
    issue_type: str,
    severity: str,
    status: str,
    description: str,
    policy_id: str,
    finding_ids: Sequence[str] = (),
    evidence_ids: Sequence[str] = (),
    blocking: bool = False,
) -> SafetyIssue:
    if not isinstance(blocking, bool):
        raise DecisionContractError("safety_issue.blocking must be boolean")
    validated_status = _require_member(status, ISSUE_STATUSES, "safety_issue.status")
    if blocking and validated_status not in {"BLOCKING", "REFERRED", "OPEN"}:
        raise DecisionContractError("blocking safety issues cannot be marked mitigated or waived")
    return SafetyIssue(
        issue_id=_require_nonempty_str(issue_id, "safety_issue.issue_id"),
        issue_type=_require_member(issue_type, SAFETY_ISSUE_TYPES, "safety_issue.issue_type"),
        severity=_require_member(severity, SAFETY_SEVERITIES, "safety_issue.severity"),
        status=validated_status,
        finding_ids=_require_unique(finding_ids, "safety_issue.finding_ids"),
        evidence_ids=_require_unique(evidence_ids, "safety_issue.evidence_ids"),
        description=_require_nonempty_str(description, "safety_issue.description"),
        policy_id=_require_nonempty_str(policy_id, "safety_issue.policy_id"),
        blocking=blocking,
    )


@dataclass(frozen=True)
class ClarificationRequirement:
    clarification_id: str
    topic: str
    question_key: str
    reason: str
    priority: str
    status: str
    required_context_keys: tuple[str, ...]
    related_finding_ids: tuple[str, ...]


def build_clarification_requirement(
    *,
    clarification_id: str,
    topic: str,
    question_key: str,
    reason: str,
    priority: str,
    status: str = "REQUIRED",
    required_context_keys: Sequence[str] = (),
    related_finding_ids: Sequence[str] = (),
) -> ClarificationRequirement:
    validated_context = _require_unique(required_context_keys, "clarification.required_context_keys")
    if status == "REQUIRED" and not validated_context:
        raise DecisionContractError("required clarification must identify at least one context key")
    return ClarificationRequirement(
        clarification_id=_require_nonempty_str(clarification_id, "clarification.clarification_id"),
        topic=_require_nonempty_str(topic, "clarification.topic"),
        question_key=_require_nonempty_str(question_key, "clarification.question_key"),
        reason=_require_nonempty_str(reason, "clarification.reason"),
        priority=_require_member(priority, CLARIFICATION_PRIORITIES, "clarification.priority"),
        status=_require_member(status, CLARIFICATION_STATUSES, "clarification.status"),
        required_context_keys=validated_context,
        related_finding_ids=_require_unique(related_finding_ids, "clarification.related_finding_ids"),
    )


@dataclass(frozen=True)
class BlockedContent:
    blocked_content_id: str
    source_type: str
    source_id: str
    reason: str
    policy_id: str
    safety_issue_ids: tuple[str, ...]


def build_blocked_content(
    *,
    blocked_content_id: str,
    source_type: str,
    source_id: str,
    reason: str,
    policy_id: str,
    safety_issue_ids: Sequence[str] = (),
) -> BlockedContent:
    return BlockedContent(
        blocked_content_id=_require_nonempty_str(blocked_content_id, "blocked_content.blocked_content_id"),
        source_type=_require_nonempty_str(source_type, "blocked_content.source_type"),
        source_id=_require_nonempty_str(source_id, "blocked_content.source_id"),
        reason=_require_member(reason, BLOCK_REASONS, "blocked_content.reason"),
        policy_id=_require_nonempty_str(policy_id, "blocked_content.policy_id"),
        safety_issue_ids=_require_unique(safety_issue_ids, "blocked_content.safety_issue_ids"),
    )


@dataclass(frozen=True)
class ApprovedResponsePacket:
    packet_id: str
    approved_finding_ids: tuple[str, ...]
    approved_evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]
    prohibited_operations: tuple[str, ...]


def build_approved_response_packet(
    *,
    packet_id: str,
    approved_finding_ids: Sequence[str] = (),
    approved_evidence_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
    prohibited_operations: Sequence[str] = (),
) -> ApprovedResponsePacket:
    findings = _require_unique(approved_finding_ids, "response_packet.approved_finding_ids")
    evidence = _require_unique(approved_evidence_ids, "response_packet.approved_evidence_ids")
    if findings and not evidence:
        raise DecisionContractError("approved response packets with findings must preserve evidence IDs")
    return ApprovedResponsePacket(
        packet_id=_require_nonempty_str(packet_id, "response_packet.packet_id"),
        approved_finding_ids=findings,
        approved_evidence_ids=evidence,
        limitation_ids=_require_unique(limitation_ids, "response_packet.limitation_ids"),
        clarification_ids=_require_unique(clarification_ids, "response_packet.clarification_ids"),
        prohibited_operations=_require_unique(prohibited_operations, "response_packet.prohibited_operations"),
    )


@dataclass(frozen=True)
class DecisionTraceEvent:
    trace_id: str
    sequence: int
    event_type: str
    finding_id: str | None
    policy_id: str | None
    decision: str
    basis: str
    input_references: tuple[str, ...]
    output_references: tuple[str, ...]
    order_marker: str


def build_trace_event(
    *,
    trace_id: str,
    sequence: int,
    event_type: str,
    decision: str,
    basis: str,
    order_marker: str,
    finding_id: str | None = None,
    policy_id: str | None = None,
    input_references: Sequence[str] = (),
    output_references: Sequence[str] = (),
) -> DecisionTraceEvent:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise DecisionContractError("trace.sequence must be a positive integer")
    if finding_id is not None:
        _require_nonempty_str(finding_id, "trace.finding_id")
    if policy_id is not None:
        _require_nonempty_str(policy_id, "trace.policy_id")
    return DecisionTraceEvent(
        trace_id=_require_nonempty_str(trace_id, "trace.trace_id"),
        sequence=sequence,
        event_type=_require_member(event_type, TRACE_EVENT_TYPES, "trace.event_type"),
        finding_id=finding_id,
        policy_id=policy_id,
        decision=_require_nonempty_str(decision, "trace.decision"),
        basis=_require_nonempty_str(basis, "trace.basis"),
        input_references=_require_unique(input_references, "trace.input_references"),
        output_references=_require_unique(output_references, "trace.output_references"),
        order_marker=_require_nonempty_str(order_marker, "trace.order_marker"),
    )


@dataclass(frozen=True)
class DecisionGateOutput:
    contract_version: str
    request_id: str
    decision_id: str
    decision: str
    finding_dispositions: tuple[FindingDisposition, ...]
    safety_issues: tuple[SafetyIssue, ...]
    clarifications: tuple[ClarificationRequirement, ...]
    response_packet: ApprovedResponsePacket | None
    blocked_content: tuple[BlockedContent, ...]
    limitations: tuple[str, ...]
    human_review_reasons: tuple[str, ...]
    confidence: float
    decision_trace: tuple[DecisionTraceEvent, ...]


def build_output(
    *,
    request_id: str,
    decision_id: str,
    decision: str,
    finding_dispositions: Sequence[FindingDisposition] = (),
    safety_issues: Sequence[SafetyIssue] = (),
    clarifications: Sequence[ClarificationRequirement] = (),
    response_packet: ApprovedResponsePacket | None = None,
    blocked_content: Sequence[BlockedContent] = (),
    limitations: Sequence[str] = (),
    human_review_reasons: Sequence[str] = (),
    confidence: float = 0.0,
    decision_trace: Sequence[DecisionTraceEvent] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> DecisionGateOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise DecisionContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    result = DecisionGateOutput(
        contract_version=contract_version,
        request_id=_require_nonempty_str(request_id, "request_id"),
        decision_id=_require_nonempty_str(decision_id, "decision_id"),
        decision=_require_member(decision, DECISION_OUTCOMES, "decision"),
        finding_dispositions=tuple(finding_dispositions),
        safety_issues=tuple(safety_issues),
        clarifications=tuple(clarifications),
        response_packet=response_packet,
        blocked_content=tuple(blocked_content),
        limitations=tuple(_require_nonempty_str(value, "limitations[]") for value in limitations),
        human_review_reasons=tuple(
            _require_nonempty_str(value, "human_review_reasons[]") for value in human_review_reasons
        ),
        confidence=_require_bounded_float(confidence, "confidence"),
        decision_trace=tuple(decision_trace),
    )
    return validate_output(result)


def validate_output(output: DecisionGateOutput) -> DecisionGateOutput:
    if not isinstance(output, DecisionGateOutput):
        raise DecisionContractError("output must be a DecisionGateOutput")
    if output.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise DecisionContractError("unsupported output contract_version")

    disposition_ids = [item.finding_id for item in output.finding_dispositions]
    issue_ids = [item.issue_id for item in output.safety_issues]
    clarification_ids = [item.clarification_id for item in output.clarifications]
    blocked_ids = [item.blocked_content_id for item in output.blocked_content]
    for values, label in (
        (disposition_ids, "finding disposition IDs"),
        (issue_ids, "safety issue IDs"),
        (clarification_ids, "clarification IDs"),
        (blocked_ids, "blocked content IDs"),
    ):
        if len(values) != len(set(values)):
            raise DecisionContractError(f"{label} must be unique")

    known_findings = set(disposition_ids)
    known_issues = set(issue_ids)
    known_clarifications = set(clarification_ids)

    for disposition in output.finding_dispositions:
        if not set(disposition.safety_issue_ids) <= known_issues:
            raise DecisionContractError("finding disposition references unknown safety issue")
        if not set(disposition.clarification_ids) <= known_clarifications:
            raise DecisionContractError("finding disposition references unknown clarification")

    for issue in output.safety_issues:
        if not set(issue.finding_ids) <= known_findings:
            raise DecisionContractError("safety issue references unknown finding")

    for clarification in output.clarifications:
        if not set(clarification.related_finding_ids) <= known_findings:
            raise DecisionContractError("clarification references unknown finding")

    for blocked in output.blocked_content:
        if not set(blocked.safety_issue_ids) <= known_issues:
            raise DecisionContractError("blocked content references unknown safety issue")

    approved_dispositions = {
        item.finding_id
        for item in output.finding_dispositions
        if item.disposition in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}
    }
    blocking_issues = [issue for issue in output.safety_issues if issue.blocking]

    if output.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        if output.response_packet is None:
            raise DecisionContractError("approved decisions require a response packet")
        if blocking_issues:
            raise DecisionContractError("approved decisions cannot contain blocking safety issues")
        if not set(output.response_packet.approved_finding_ids) <= approved_dispositions:
            raise DecisionContractError("response packet references a finding that was not approved")
    elif output.response_packet is not None and output.response_packet.approved_finding_ids:
        raise DecisionContractError("non-approved decisions cannot expose approved findings")

    if output.decision == "CLARIFICATION_REQUIRED":
        if not any(item.status == "REQUIRED" for item in output.clarifications):
            raise DecisionContractError("clarification-required decisions need a required clarification")
    if output.decision == "HUMAN_REVIEW_REQUIRED" and not output.human_review_reasons:
        raise DecisionContractError("human-review decisions require at least one review reason")
    if output.decision == "BLOCKED" and not (blocking_issues or output.blocked_content):
        raise DecisionContractError("blocked decisions require blocking evidence")

    trace_sequences = [event.sequence for event in output.decision_trace]
    if trace_sequences != sorted(trace_sequences) or len(trace_sequences) != len(set(trace_sequences)):
        raise DecisionContractError("decision trace sequence values must be unique and ordered")
    for event in output.decision_trace:
        if event.finding_id is not None and event.finding_id not in known_findings:
            raise DecisionContractError("trace references unknown finding")

    return output
