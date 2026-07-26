"""Executable contracts for the deterministic Response Assembler (MO-020)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import DecisionGateOutput
from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
RESPONSE_STATUSES = frozenset(
    {
        "ANSWER",
        "ANSWER_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED",
        "INSUFFICIENT_EVIDENCE",
        "CONFLICTING_EVIDENCE",
        "UNSUPPORTED",
        "BLOCKED",
        "OUT_OF_SCOPE",
        "INVALID_INPUT",
    }
)
RESPONSE_FORMATS = frozenset({"STANDARD", "COMPACT", "DETAILED", "ADVISOR_BRIEF"})
SECTION_TYPES = frozenset(
    {
        "DIRECT_ANSWER",
        "EXPLANATION",
        "CONDITION",
        "IMPACT",
        "LIMITATION",
        "EVIDENCE",
        "ASSUMPTION",
        "CLARIFICATION",
        "ADVISOR_TALKING_POINT",
        "INTERNAL_NOTE",
    }
)
SECTION_STATUSES = frozenset({"INCLUDED", "WITHHELD", "REQUIRES_REVIEW"})
EVIDENCE_REFERENCE_TYPES = frozenset({"EVIDENCE", "DOCUMENT", "SOURCE", "FINDING"})
TRACE_EVENT_TYPES = frozenset(
    {
        "RESPONSE_ASSEMBLY_STARTED",
        "INPUT_VALIDATED",
        "DECISION_MAPPED",
        "EXPLANATION_SECTION_RECEIVED",
        "RESPONSE_SECTION_CREATED",
        "EVIDENCE_REFERENCE_ATTACHED",
        "LIMITATION_ATTACHED",
        "ASSUMPTION_ATTACHED",
        "CLARIFICATION_ATTACHED",
        "RESPONSE_VALIDATED",
        "RESPONSE_ASSEMBLY_COMPLETED",
    }
)


class ResponseContractError(ValueError):
    """Raised when a Response Assembler contract is invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResponseContractError(f"{label} must be a non-empty string")
    return value


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ResponseContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_bounded_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ResponseContractError(f"{label} must be a number")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ResponseContractError(f"{label} must be between 0 and 1; got {numeric}")
    return numeric


def _require_unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_require_nonempty_str(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise ResponseContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class ResponseAssemblerInput:
    contract_version: str
    request_id: str
    decision_output: DecisionGateOutput
    explanation_output: ExplanationGeneratorOutput
    response_format: str
    assembly_context: Mapping[str, object]


def build_input(
    *,
    request_id: str,
    decision_output: DecisionGateOutput,
    explanation_output: ExplanationGeneratorOutput,
    response_format: str = "STANDARD",
    assembly_context: Mapping[str, object] | None = None,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> ResponseAssemblerInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ResponseContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(decision_output, DecisionGateOutput):
        raise ResponseContractError("decision_output must be a validated DecisionGateOutput")
    if not isinstance(explanation_output, ExplanationGeneratorOutput):
        raise ResponseContractError("explanation_output must be a validated ExplanationGeneratorOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if decision_output.request_id != validated_request_id:
        raise ResponseContractError("request_id must match decision_output")
    if explanation_output.request_id != validated_request_id:
        raise ResponseContractError("request_id must match explanation_output")

    decision = decision_output.decision
    explanation_status = explanation_output.explanation_status
    if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        if explanation_status not in {"DRAFTED", "DRAFTED_WITH_LIMITATIONS"}:
            raise ResponseContractError("approved decisions require a drafted explanation")
    elif decision == "CLARIFICATION_REQUIRED":
        if explanation_status != "CLARIFICATION_DRAFTED":
            raise ResponseContractError("clarification decisions require a clarification draft")
    else:
        raise ResponseContractError("decision_output is not eligible for response assembly")

    return ResponseAssemblerInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        decision_output=decision_output,
        explanation_output=explanation_output,
        response_format=_require_member(response_format, RESPONSE_FORMATS, "response_format"),
        assembly_context=dict(assembly_context or {}),
    )


@dataclass(frozen=True)
class ResponseSection:
    section_id: str
    section_type: str
    status: str
    text: str
    explanation_section_ids: tuple[str, ...]
    approved_finding_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    assumption_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]


def build_section(
    *,
    section_id: str,
    section_type: str,
    status: str,
    text: str,
    explanation_section_ids: Sequence[str] = (),
    approved_finding_ids: Sequence[str] = (),
    evidence_reference_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    assumption_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
) -> ResponseSection:
    validated_type = _require_member(section_type, SECTION_TYPES, "section.section_type")
    validated_status = _require_member(status, SECTION_STATUSES, "section.status")
    explanation_ids = _require_unique(explanation_section_ids, "section.explanation_section_ids")
    findings = _require_unique(approved_finding_ids, "section.approved_finding_ids")
    evidence = _require_unique(evidence_reference_ids, "section.evidence_reference_ids")
    clarifications = _require_unique(clarification_ids, "section.clarification_ids")
    if validated_status == "INCLUDED" and findings and not evidence:
        raise ResponseContractError("included finding-backed sections must preserve evidence references")
    if validated_type == "CLARIFICATION" and not clarifications:
        raise ResponseContractError("clarification sections must reference clarification IDs")
    if validated_type != "CLARIFICATION" and clarifications:
        raise ResponseContractError("only clarification sections may reference clarification IDs")
    return ResponseSection(
        section_id=_require_nonempty_str(section_id, "section.section_id"),
        section_type=validated_type,
        status=validated_status,
        text=_require_nonempty_str(text, "section.text"),
        explanation_section_ids=explanation_ids,
        approved_finding_ids=findings,
        evidence_reference_ids=evidence,
        limitation_ids=_require_unique(limitation_ids, "section.limitation_ids"),
        assumption_ids=_require_unique(assumption_ids, "section.assumption_ids"),
        clarification_ids=clarifications,
    )


@dataclass(frozen=True)
class EvidenceReference:
    reference_id: str
    reference_type: str
    source_id: str
    label: str
    locator: str | None
    approved_finding_ids: tuple[str, ...]


def build_evidence_reference(
    *,
    reference_id: str,
    reference_type: str,
    source_id: str,
    label: str,
    locator: str | None = None,
    approved_finding_ids: Sequence[str] = (),
) -> EvidenceReference:
    if locator is not None:
        _require_nonempty_str(locator, "evidence_reference.locator")
    return EvidenceReference(
        reference_id=_require_nonempty_str(reference_id, "evidence_reference.reference_id"),
        reference_type=_require_member(reference_type, EVIDENCE_REFERENCE_TYPES, "evidence_reference.reference_type"),
        source_id=_require_nonempty_str(source_id, "evidence_reference.source_id"),
        label=_require_nonempty_str(label, "evidence_reference.label"),
        locator=locator,
        approved_finding_ids=_require_unique(approved_finding_ids, "evidence_reference.approved_finding_ids"),
    )


@dataclass(frozen=True)
class ResponseTraceEvent:
    trace_id: str
    sequence: int
    event_type: str
    section_id: str | None
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
    section_id: str | None = None,
    input_references: Sequence[str] = (),
    output_references: Sequence[str] = (),
) -> ResponseTraceEvent:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ResponseContractError("trace.sequence must be a positive integer")
    if section_id is not None:
        _require_nonempty_str(section_id, "trace.section_id")
    return ResponseTraceEvent(
        trace_id=_require_nonempty_str(trace_id, "trace.trace_id"),
        sequence=sequence,
        event_type=_require_member(event_type, TRACE_EVENT_TYPES, "trace.event_type"),
        section_id=section_id,
        decision=_require_nonempty_str(decision, "trace.decision"),
        basis=_require_nonempty_str(basis, "trace.basis"),
        input_references=_require_unique(input_references, "trace.input_references"),
        output_references=_require_unique(output_references, "trace.output_references"),
        order_marker=_require_nonempty_str(order_marker, "trace.order_marker"),
    )


@dataclass(frozen=True)
class ResponseAssemblerOutput:
    contract_version: str
    request_id: str
    response_id: str
    response_status: str
    audience: str
    response_format: str
    direct_answer: str | None
    sections: tuple[ResponseSection, ...]
    evidence_references: tuple[EvidenceReference, ...]
    limitations: tuple[str, ...]
    assumptions: tuple[str, ...]
    clarification_questions: tuple[str, ...]
    confidence: float
    response_trace: tuple[ResponseTraceEvent, ...]


def build_output(
    *,
    request_id: str,
    response_id: str,
    response_status: str,
    audience: str,
    response_format: str,
    direct_answer: str | None = None,
    sections: Sequence[ResponseSection] = (),
    evidence_references: Sequence[EvidenceReference] = (),
    limitations: Sequence[str] = (),
    assumptions: Sequence[str] = (),
    clarification_questions: Sequence[str] = (),
    confidence: float = 0.0,
    response_trace: Sequence[ResponseTraceEvent] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> ResponseAssemblerOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ResponseContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if direct_answer is not None:
        _require_nonempty_str(direct_answer, "direct_answer")
    output = ResponseAssemblerOutput(
        contract_version=contract_version,
        request_id=_require_nonempty_str(request_id, "request_id"),
        response_id=_require_nonempty_str(response_id, "response_id"),
        response_status=_require_member(response_status, RESPONSE_STATUSES, "response_status"),
        audience=_require_nonempty_str(audience, "audience"),
        response_format=_require_member(response_format, RESPONSE_FORMATS, "response_format"),
        direct_answer=direct_answer,
        sections=tuple(sections),
        evidence_references=tuple(evidence_references),
        limitations=tuple(_require_nonempty_str(value, "limitations[]") for value in limitations),
        assumptions=tuple(_require_nonempty_str(value, "assumptions[]") for value in assumptions),
        clarification_questions=tuple(
            _require_nonempty_str(value, "clarification_questions[]") for value in clarification_questions
        ),
        confidence=_require_bounded_float(confidence, "confidence"),
        response_trace=tuple(response_trace),
    )
    return validate_output(output)


def validate_output(output: ResponseAssemblerOutput) -> ResponseAssemblerOutput:
    if not isinstance(output, ResponseAssemblerOutput):
        raise ResponseContractError("output must be a ResponseAssemblerOutput")
    if output.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ResponseContractError("unsupported output contract_version")

    section_ids = [item.section_id for item in output.sections]
    reference_ids = [item.reference_id for item in output.evidence_references]
    if len(section_ids) != len(set(section_ids)):
        raise ResponseContractError("response section IDs must be unique")
    if len(reference_ids) != len(set(reference_ids)):
        raise ResponseContractError("evidence reference IDs must be unique")

    known_sections = set(section_ids)
    known_references = set(reference_ids)
    for section in output.sections:
        if not set(section.evidence_reference_ids) <= known_references:
            raise ResponseContractError("response section references unknown evidence reference")

    sequences = [item.sequence for item in output.response_trace]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise ResponseContractError("response trace sequence values must be unique and ordered")
    for event in output.response_trace:
        if event.section_id is not None and event.section_id not in known_sections:
            raise ResponseContractError("response trace references unknown section")

    included = [item for item in output.sections if item.status == "INCLUDED"]
    if output.response_status in {"ANSWER", "ANSWER_WITH_LIMITATIONS"}:
        if not output.direct_answer:
            raise ResponseContractError("answer statuses require a direct answer")
        if not included:
            raise ResponseContractError("answer statuses require at least one included section")
        if any(item.section_type == "CLARIFICATION" for item in included):
            raise ResponseContractError("answer statuses cannot include clarification sections")
        if output.clarification_questions:
            raise ResponseContractError("answer statuses cannot include clarification questions")
    if output.response_status == "ANSWER_WITH_LIMITATIONS" and not output.limitations:
        raise ResponseContractError("answer-with-limitations status requires limitations")
    if output.response_status == "CLARIFICATION_REQUIRED":
        if output.direct_answer is not None:
            raise ResponseContractError("clarification responses cannot include a direct answer")
        if not output.clarification_questions:
            raise ResponseContractError("clarification responses require clarification questions")
        if not included or any(item.section_type != "CLARIFICATION" for item in included):
            raise ResponseContractError("clarification responses may include clarification sections only")
        if output.evidence_references:
            raise ResponseContractError("clarification responses cannot expose evidence references")

    if output.response_status in {
        "INSUFFICIENT_EVIDENCE",
        "CONFLICTING_EVIDENCE",
        "UNSUPPORTED",
        "BLOCKED",
        "OUT_OF_SCOPE",
    }:
        if output.direct_answer is not None or included or output.evidence_references:
            raise ResponseContractError("non-answer statuses cannot expose answer content or evidence")

    return output
