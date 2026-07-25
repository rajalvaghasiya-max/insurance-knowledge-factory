"""Contracts for controlled, evidence-locked LLM explanation rendering (MO-022)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import DecisionGateOutput
from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
RENDERING_STATUSES = frozenset(
    {
        "RENDERED",
        "RENDERED_WITH_LIMITATIONS",
        "FALLBACK_USED",
        "VALIDATION_FAILED",
        "PROVIDER_FAILED",
        "BLOCKED",
        "NOT_REQUIRED",
        "INVALID_INPUT",
    }
)
FALLBACK_REASONS = frozenset(
    {
        "PROVIDER_ERROR",
        "TIMEOUT",
        "INVALID_STRUCTURE",
        "FIDELITY_FAILURE",
        "UNSUPPORTED_CONTENT",
        "NUMERIC_CHANGE",
        "MISSING_CONDITION",
        "MISSING_LIMITATION",
        "EVIDENCE_MISMATCH",
        "DECISION_SCOPE_MISMATCH",
    }
)
PROVIDER_RESPONSE_STATUSES = frozenset({"SUCCEEDED", "FAILED", "TIMEOUT", "INVALID_RESPONSE"})
FIDELITY_STATUSES = frozenset({"VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED", "REQUIRES_REVIEW"})
FIDELITY_CHECK_STATUSES = frozenset({"PASSED", "FAILED", "NOT_APPLICABLE", "REQUIRES_REVIEW"})
FIDELITY_CHECK_TYPES = frozenset(
    {
        "STRUCTURE_VALID",
        "FINDING_SCOPE_PRESERVED",
        "EVIDENCE_PRESERVED",
        "NUMERIC_FIDELITY",
        "CONDITION_PRESERVED",
        "LIMITATION_PRESERVED",
        "CLARIFICATION_SCOPE_PRESERVED",
        "NO_NEW_FACTS",
        "NO_NEW_REASONING",
        "NO_RECOMMENDATION",
        "NO_UNAPPROVED_EXAMPLE",
    }
)
TRACE_EVENT_TYPES = frozenset(
    {
        "RENDERING_STARTED",
        "INPUT_VALIDATED",
        "PACKET_BUILT",
        "PROVIDER_REQUESTED",
        "PROVIDER_RESPONDED",
        "CANDIDATE_PARSED",
        "FIDELITY_VALIDATED",
        "FALLBACK_SELECTED",
        "RENDERING_COMPLETED",
    }
)


class LLMRenderingContractError(ValueError):
    """Raised when a controlled LLM rendering contract is invalid."""


def _nonempty(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMRenderingContractError(f"{label} must be a non-empty string")
    return value


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise LLMRenderingContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_nonempty(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise LLMRenderingContractError(f"{label} values must be unique")
    return result


def _bounded(value: object, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMRenderingContractError(f"{label} must be numeric")
    number = float(value)
    if not low <= number <= high:
        raise LLMRenderingContractError(f"{label} must be between {low} and {high}; got {number}")
    return number


def _positive_int(value: object, label: str, *, allow_zero: bool = False) -> int:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        wording = "non-negative" if allow_zero else "positive"
        raise LLMRenderingContractError(f"{label} must be a {wording} integer")
    return value


@dataclass(frozen=True)
class LLMRenderingInput:
    contract_version: str
    request_id: str
    decision_output: DecisionGateOutput
    deterministic_explanation: ExplanationGeneratorOutput
    provider_name: str
    model_name: str
    style_context: Mapping[str, object]


def build_input(
    *,
    request_id: str,
    decision_output: DecisionGateOutput,
    deterministic_explanation: ExplanationGeneratorOutput,
    provider_name: str,
    model_name: str,
    style_context: Mapping[str, object] | None = None,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> LLMRenderingInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise LLMRenderingContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(decision_output, DecisionGateOutput):
        raise LLMRenderingContractError("decision_output must be a validated DecisionGateOutput")
    if not isinstance(deterministic_explanation, ExplanationGeneratorOutput):
        raise LLMRenderingContractError("deterministic_explanation must be a validated ExplanationGeneratorOutput")
    rid = _nonempty(request_id, "request_id")
    if decision_output.request_id != rid or deterministic_explanation.request_id != rid:
        raise LLMRenderingContractError("request_id must match decision and deterministic explanation outputs")
    if decision_output.decision not in {"APPROVED", "APPROVED_WITH_LIMITATIONS", "CLARIFICATION_REQUIRED"}:
        raise LLMRenderingContractError("decision_output is not eligible for controlled rendering")
    if deterministic_explanation.explanation_status not in {
        "DRAFTED",
        "DRAFTED_WITH_LIMITATIONS",
        "CLARIFICATION_DRAFTED",
    }:
        raise LLMRenderingContractError("deterministic explanation is not eligible for rendering")
    if deterministic_explanation.fidelity_status not in {"VERIFIED", "VERIFIED_WITH_LIMITATIONS"}:
        raise LLMRenderingContractError("deterministic explanation must be fidelity verified")
    if decision_output.decision == "CLARIFICATION_REQUIRED":
        if deterministic_explanation.explanation_status != "CLARIFICATION_DRAFTED":
            raise LLMRenderingContractError("clarification decision requires clarification-only deterministic explanation")
    elif deterministic_explanation.explanation_status == "CLARIFICATION_DRAFTED":
        raise LLMRenderingContractError("approved decision cannot use clarification-only deterministic explanation")
    return LLMRenderingInput(
        contract_version=contract_version,
        request_id=rid,
        decision_output=decision_output,
        deterministic_explanation=deterministic_explanation,
        provider_name=_nonempty(provider_name, "provider_name"),
        model_name=_nonempty(model_name, "model_name"),
        style_context=dict(style_context or {}),
    )


@dataclass(frozen=True)
class EvidenceLockedRenderingPacket:
    packet_id: str
    request_id: str
    decision_id: str
    explanation_id: str
    audience: str
    reading_level: str
    explanation_mode: str
    source_section_ids: tuple[str, ...]
    approved_finding_ids: tuple[str, ...]
    approved_evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]
    prohibited_operations: tuple[str, ...]


def build_rendering_packet(
    *,
    packet_id: str,
    request_id: str,
    decision_id: str,
    explanation_id: str,
    audience: str,
    reading_level: str,
    explanation_mode: str,
    source_section_ids: Sequence[str],
    approved_finding_ids: Sequence[str] = (),
    approved_evidence_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
    prohibited_operations: Sequence[str] = (),
) -> EvidenceLockedRenderingPacket:
    sections = _unique(source_section_ids, "packet.source_section_ids")
    if not sections:
        raise LLMRenderingContractError("rendering packet requires at least one source section")
    findings = _unique(approved_finding_ids, "packet.approved_finding_ids")
    evidence = _unique(approved_evidence_ids, "packet.approved_evidence_ids")
    clarifications = _unique(clarification_ids, "packet.clarification_ids")
    if findings and not evidence:
        raise LLMRenderingContractError("finding-backed rendering packets must preserve approved evidence IDs")
    if findings and clarifications:
        raise LLMRenderingContractError("rendering packet cannot mix approved findings and clarification scope")
    if not findings and not clarifications:
        raise LLMRenderingContractError("rendering packet requires approved finding or clarification scope")
    return EvidenceLockedRenderingPacket(
        packet_id=_nonempty(packet_id, "packet.packet_id"),
        request_id=_nonempty(request_id, "packet.request_id"),
        decision_id=_nonempty(decision_id, "packet.decision_id"),
        explanation_id=_nonempty(explanation_id, "packet.explanation_id"),
        audience=_nonempty(audience, "packet.audience"),
        reading_level=_nonempty(reading_level, "packet.reading_level"),
        explanation_mode=_nonempty(explanation_mode, "packet.explanation_mode"),
        source_section_ids=sections,
        approved_finding_ids=findings,
        approved_evidence_ids=evidence,
        limitation_ids=_unique(limitation_ids, "packet.limitation_ids"),
        clarification_ids=clarifications,
        prohibited_operations=_unique(prohibited_operations, "packet.prohibited_operations"),
    )


@dataclass(frozen=True)
class ProviderRenderRequest:
    provider_request_id: str
    request_id: str
    rendering_id: str
    provider_name: str
    model_name: str
    temperature: float
    max_output_tokens: int
    structured_output: bool
    tools_enabled: bool
    browsing_enabled: bool
    memory_enabled: bool
    packet: EvidenceLockedRenderingPacket


def build_provider_request(
    *,
    provider_request_id: str,
    request_id: str,
    rendering_id: str,
    provider_name: str,
    model_name: str,
    packet: EvidenceLockedRenderingPacket,
    temperature: float = 0.0,
    max_output_tokens: int = 1200,
    structured_output: bool = True,
    tools_enabled: bool = False,
    browsing_enabled: bool = False,
    memory_enabled: bool = False,
) -> ProviderRenderRequest:
    for value, label in (
        (structured_output, "structured_output"),
        (tools_enabled, "tools_enabled"),
        (browsing_enabled, "browsing_enabled"),
        (memory_enabled, "memory_enabled"),
    ):
        if not isinstance(value, bool):
            raise LLMRenderingContractError(f"provider_request.{label} must be boolean")
    rid = _nonempty(request_id, "provider_request.request_id")
    if packet.request_id != rid:
        raise LLMRenderingContractError("provider request_id must match rendering packet")
    if not structured_output:
        raise LLMRenderingContractError("controlled renderer requires structured output")
    if tools_enabled or browsing_enabled or memory_enabled:
        raise LLMRenderingContractError("controlled renderer forbids tools, browsing, and memory")
    return ProviderRenderRequest(
        provider_request_id=_nonempty(provider_request_id, "provider_request.provider_request_id"),
        request_id=rid,
        rendering_id=_nonempty(rendering_id, "provider_request.rendering_id"),
        provider_name=_nonempty(provider_name, "provider_request.provider_name"),
        model_name=_nonempty(model_name, "provider_request.model_name"),
        temperature=_bounded(temperature, "provider_request.temperature", 0.0, 0.3),
        max_output_tokens=_positive_int(max_output_tokens, "provider_request.max_output_tokens"),
        structured_output=structured_output,
        tools_enabled=tools_enabled,
        browsing_enabled=browsing_enabled,
        memory_enabled=memory_enabled,
        packet=packet,
    )


@dataclass(frozen=True)
class CandidateRenderedSection:
    section_id: str
    source_section_id: str
    section_type: str
    text: str
    approved_finding_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]


def build_candidate_section(
    *,
    section_id: str,
    source_section_id: str,
    section_type: str,
    text: str,
    approved_finding_ids: Sequence[str] = (),
    evidence_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
) -> CandidateRenderedSection:
    findings = _unique(approved_finding_ids, "candidate.approved_finding_ids")
    evidence = _unique(evidence_ids, "candidate.evidence_ids")
    clarifications = _unique(clarification_ids, "candidate.clarification_ids")
    if findings and not evidence:
        raise LLMRenderingContractError("candidate finding-backed sections must preserve evidence IDs")
    if findings and clarifications:
        raise LLMRenderingContractError("candidate section cannot mix finding and clarification scope")
    return CandidateRenderedSection(
        section_id=_nonempty(section_id, "candidate.section_id"),
        source_section_id=_nonempty(source_section_id, "candidate.source_section_id"),
        section_type=_nonempty(section_type, "candidate.section_type"),
        text=_nonempty(text, "candidate.text"),
        approved_finding_ids=findings,
        evidence_ids=evidence,
        limitation_ids=_unique(limitation_ids, "candidate.limitation_ids"),
        clarification_ids=clarifications,
    )


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


def build_token_usage(*, input_tokens: int, output_tokens: int, total_tokens: int) -> TokenUsage:
    input_value = _positive_int(input_tokens, "usage.input_tokens", allow_zero=True)
    output_value = _positive_int(output_tokens, "usage.output_tokens", allow_zero=True)
    total_value = _positive_int(total_tokens, "usage.total_tokens", allow_zero=True)
    if total_value != input_value + output_value:
        raise LLMRenderingContractError("usage.total_tokens must equal input_tokens + output_tokens")
    return TokenUsage(input_tokens=input_value, output_tokens=output_value, total_tokens=total_value)


@dataclass(frozen=True)
class ProviderRenderResponse:
    provider_response_id: str
    provider_request_id: str
    status: str
    candidate_sections: tuple[CandidateRenderedSection, ...]
    token_usage: TokenUsage | None
    finish_reason: str | None
    error_message: str | None
    provider_metadata: Mapping[str, object]


def build_provider_response(
    *,
    provider_response_id: str,
    provider_request_id: str,
    status: str,
    candidate_sections: Sequence[CandidateRenderedSection] = (),
    token_usage: TokenUsage | None = None,
    finish_reason: str | None = None,
    error_message: str | None = None,
    provider_metadata: Mapping[str, object] | None = None,
) -> ProviderRenderResponse:
    validated_status = _member(status, PROVIDER_RESPONSE_STATUSES, "provider_response.status")
    sections = tuple(candidate_sections)
    ids = [section.section_id for section in sections]
    if len(ids) != len(set(ids)):
        raise LLMRenderingContractError("provider response candidate section IDs must be unique")
    if validated_status == "SUCCEEDED" and not sections:
        raise LLMRenderingContractError("successful provider response requires candidate sections")
    if validated_status != "SUCCEEDED" and sections:
        raise LLMRenderingContractError("failed provider response cannot expose candidate sections")
    if validated_status != "SUCCEEDED" and not error_message:
        raise LLMRenderingContractError("failed provider response requires error_message")
    if finish_reason is not None:
        _nonempty(finish_reason, "provider_response.finish_reason")
    return ProviderRenderResponse(
        provider_response_id=_nonempty(provider_response_id, "provider_response.provider_response_id"),
        provider_request_id=_nonempty(provider_request_id, "provider_response.provider_request_id"),
        status=validated_status,
        candidate_sections=sections,
        token_usage=token_usage,
        finish_reason=finish_reason,
        error_message=error_message,
        provider_metadata=dict(provider_metadata or {}),
    )


@dataclass(frozen=True)
class RenderingFidelityCheck:
    check_id: str
    check_type: str
    status: str
    source_section_ids: tuple[str, ...]
    candidate_section_ids: tuple[str, ...]
    description: str


def build_fidelity_check(
    *,
    check_id: str,
    check_type: str,
    status: str,
    description: str,
    source_section_ids: Sequence[str] = (),
    candidate_section_ids: Sequence[str] = (),
) -> RenderingFidelityCheck:
    return RenderingFidelityCheck(
        check_id=_nonempty(check_id, "fidelity_check.check_id"),
        check_type=_member(check_type, FIDELITY_CHECK_TYPES, "fidelity_check.check_type"),
        status=_member(status, FIDELITY_CHECK_STATUSES, "fidelity_check.status"),
        source_section_ids=_unique(source_section_ids, "fidelity_check.source_section_ids"),
        candidate_section_ids=_unique(candidate_section_ids, "fidelity_check.candidate_section_ids"),
        description=_nonempty(description, "fidelity_check.description"),
    )


@dataclass(frozen=True)
class FallbackRecord:
    fallback_id: str
    reason: str
    deterministic_explanation_id: str
    rejected_provider_response_id: str | None
    description: str


def build_fallback_record(
    *,
    fallback_id: str,
    reason: str,
    deterministic_explanation_id: str,
    description: str,
    rejected_provider_response_id: str | None = None,
) -> FallbackRecord:
    if rejected_provider_response_id is not None:
        _nonempty(rejected_provider_response_id, "fallback.rejected_provider_response_id")
    return FallbackRecord(
        fallback_id=_nonempty(fallback_id, "fallback.fallback_id"),
        reason=_member(reason, FALLBACK_REASONS, "fallback.reason"),
        deterministic_explanation_id=_nonempty(
            deterministic_explanation_id, "fallback.deterministic_explanation_id"
        ),
        rejected_provider_response_id=rejected_provider_response_id,
        description=_nonempty(description, "fallback.description"),
    )


@dataclass(frozen=True)
class LLMRenderingTraceEvent:
    trace_id: str
    sequence: int
    event_type: str
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
    input_references: Sequence[str] = (),
    output_references: Sequence[str] = (),
) -> LLMRenderingTraceEvent:
    return LLMRenderingTraceEvent(
        trace_id=_nonempty(trace_id, "trace.trace_id"),
        sequence=_positive_int(sequence, "trace.sequence"),
        event_type=_member(event_type, TRACE_EVENT_TYPES, "trace.event_type"),
        decision=_nonempty(decision, "trace.decision"),
        basis=_nonempty(basis, "trace.basis"),
        input_references=_unique(input_references, "trace.input_references"),
        output_references=_unique(output_references, "trace.output_references"),
        order_marker=_nonempty(order_marker, "trace.order_marker"),
    )


@dataclass(frozen=True)
class LLMRenderingOutput:
    contract_version: str
    request_id: str
    rendering_id: str
    provider_name: str
    model_name: str
    rendered_sections: tuple[CandidateRenderedSection, ...]
    provider_response: ProviderRenderResponse | None
    fidelity_checks: tuple[RenderingFidelityCheck, ...]
    fidelity_status: str
    fallback: FallbackRecord | None
    rendering_status: str
    limitations: tuple[str, ...]
    confidence: float
    rendering_trace: tuple[LLMRenderingTraceEvent, ...]


def build_output(
    *,
    request_id: str,
    rendering_id: str,
    provider_name: str,
    model_name: str,
    rendered_sections: Sequence[CandidateRenderedSection] = (),
    provider_response: ProviderRenderResponse | None = None,
    fidelity_checks: Sequence[RenderingFidelityCheck] = (),
    fidelity_status: str,
    fallback: FallbackRecord | None = None,
    rendering_status: str,
    limitations: Sequence[str] = (),
    confidence: float = 0.0,
    rendering_trace: Sequence[LLMRenderingTraceEvent] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> LLMRenderingOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise LLMRenderingContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    output = LLMRenderingOutput(
        contract_version=contract_version,
        request_id=_nonempty(request_id, "request_id"),
        rendering_id=_nonempty(rendering_id, "rendering_id"),
        provider_name=_nonempty(provider_name, "provider_name"),
        model_name=_nonempty(model_name, "model_name"),
        rendered_sections=tuple(rendered_sections),
        provider_response=provider_response,
        fidelity_checks=tuple(fidelity_checks),
        fidelity_status=_member(fidelity_status, FIDELITY_STATUSES, "fidelity_status"),
        fallback=fallback,
        rendering_status=_member(rendering_status, RENDERING_STATUSES, "rendering_status"),
        limitations=tuple(_nonempty(item, "limitations[]") for item in limitations),
        confidence=_bounded(confidence, "confidence", 0.0, 1.0),
        rendering_trace=tuple(rendering_trace),
    )
    return validate_output(output)


def validate_output(output: LLMRenderingOutput) -> LLMRenderingOutput:
    if not isinstance(output, LLMRenderingOutput):
        raise LLMRenderingContractError("output must be an LLMRenderingOutput")
    section_ids = [section.section_id for section in output.rendered_sections]
    check_ids = [check.check_id for check in output.fidelity_checks]
    if len(section_ids) != len(set(section_ids)):
        raise LLMRenderingContractError("rendered section IDs must be unique")
    if len(check_ids) != len(set(check_ids)):
        raise LLMRenderingContractError("fidelity check IDs must be unique")
    known_sections = set(section_ids)
    for check in output.fidelity_checks:
        if not set(check.candidate_section_ids) <= known_sections:
            raise LLMRenderingContractError("fidelity check references unknown candidate section")
    sequences = [event.sequence for event in output.rendering_trace]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise LLMRenderingContractError("rendering trace sequence values must be unique and ordered")

    if output.rendering_status == "FALLBACK_USED" and output.fallback is None:
        raise LLMRenderingContractError("fallback-used status requires fallback record")

    failed_checks = [check for check in output.fidelity_checks if check.status == "FAILED"]
    review_checks = [check for check in output.fidelity_checks if check.status == "REQUIRES_REVIEW"]
    if output.fidelity_status == "VERIFIED" and (failed_checks or review_checks):
        raise LLMRenderingContractError("verified fidelity cannot contain failed or review checks")
    if output.fidelity_status == "FAILED" and not failed_checks:
        if output.rendering_status not in {"PROVIDER_FAILED", "BLOCKED", "INVALID_INPUT"}:
            raise LLMRenderingContractError("failed fidelity requires at least one failed check")
    if output.fidelity_status == "REQUIRES_REVIEW" and not review_checks:
        raise LLMRenderingContractError("review fidelity requires at least one review check")

    if output.rendering_status in {"RENDERED", "RENDERED_WITH_LIMITATIONS"}:
        if not output.rendered_sections:
            raise LLMRenderingContractError("rendered status requires rendered sections")
        if output.provider_response is None or output.provider_response.status != "SUCCEEDED":
            raise LLMRenderingContractError("rendered status requires successful provider response")
        if output.fidelity_status not in {"VERIFIED", "VERIFIED_WITH_LIMITATIONS"}:
            raise LLMRenderingContractError("rendered status requires verified fidelity")
        if output.fallback is not None:
            raise LLMRenderingContractError("rendered status cannot include fallback")
    elif output.rendering_status == "FALLBACK_USED":
        if output.rendered_sections:
            raise LLMRenderingContractError("fallback-used output cannot expose rejected rendered sections")
    elif output.rendering_status in {"PROVIDER_FAILED", "VALIDATION_FAILED"}:
        if output.rendered_sections:
            raise LLMRenderingContractError("failed rendering output cannot expose rendered sections")
    if output.rendering_status == "RENDERED_WITH_LIMITATIONS" and not output.limitations:
        raise LLMRenderingContractError("rendered-with-limitations status requires limitations")
    return output
