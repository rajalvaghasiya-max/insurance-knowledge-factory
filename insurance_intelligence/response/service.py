"""Executable deterministic Response Assembler service for MO-020E."""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.contracts.response import (
    ResponseAssemblerInput,
    ResponseAssemblerOutput,
    build_output,
    build_trace_event,
)
from insurance_intelligence.response.assembler import assemble_sections
from insurance_intelligence.response.registry import ResponseFormatRegistry
from insurance_intelligence.response.validator import validate_response_draft


class ResponseServiceError(ValueError):
    """Raised when a response cannot be assembled and verified safely."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _response_status(decision: str) -> str:
    mapping = {
        "APPROVED": "ANSWER",
        "APPROVED_WITH_LIMITATIONS": "ANSWER_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUIRED",
    }
    try:
        return mapping[decision]
    except KeyError as exc:
        raise ResponseServiceError(f"unsupported decision for response assembly: {decision}") from exc


def assemble_response(
    assembler_input: ResponseAssemblerInput,
    registry: ResponseFormatRegistry,
) -> ResponseAssemblerOutput:
    """Select, assemble, validate, and package one deterministic response."""
    if not isinstance(assembler_input, ResponseAssemblerInput):
        raise ResponseServiceError("assembler_input must be a ResponseAssemblerInput")
    if not isinstance(registry, ResponseFormatRegistry):
        raise ResponseServiceError("registry must be a ResponseFormatRegistry")

    decision = assembler_input.decision_output
    explanation = assembler_input.explanation_output
    response_status = _response_status(decision.decision)
    definition = registry.select_one(
        response_format=assembler_input.response_format,
        audience=explanation.audience,
        response_status=response_status,
    )
    draft = assemble_sections(assembler_input, definition)
    integrity = validate_response_draft(assembler_input, definition, draft)
    if not integrity.verified:
        raise ResponseServiceError(
            f"assembled response failed integrity validation: {integrity.integrity_status}"
        )

    response_id = _stable_id(
        "response",
        assembler_input.request_id,
        decision.decision_id,
        explanation.explanation_id,
        definition.format_id,
        definition.format_version,
        integrity.validation_id,
    )

    trace = []

    def add(event_type: str, decision_text: str, basis: str, *, section_id: str | None = None,
            inputs: tuple[str, ...] = (), outputs: tuple[str, ...] = ()) -> None:
        sequence = len(trace) + 1
        trace.append(
            build_trace_event(
                trace_id=_stable_id("response-trace", response_id, sequence, event_type, section_id or ""),
                sequence=sequence,
                event_type=event_type,
                section_id=section_id,
                decision=decision_text,
                basis=basis,
                input_references=inputs,
                output_references=outputs,
                order_marker=f"{sequence:04d}",
            )
        )

    add(
        "RESPONSE_ASSEMBLY_STARTED",
        "STARTED",
        "validated Decision Gate and Explanation Generator outputs received",
        inputs=(decision.decision_id, explanation.explanation_id),
    )
    add(
        "INPUT_VALIDATED",
        "VALID",
        "cross-stage request identity and eligibility were validated by the response contract",
        inputs=(assembler_input.request_id,),
    )
    add(
        "DECISION_MAPPED",
        response_status,
        "Decision Gate outcome mapped deterministically to response status",
        inputs=(decision.decision,),
        outputs=(response_status,),
    )
    for section in draft.sections:
        add(
            "EXPLANATION_SECTION_RECEIVED",
            "RECEIVED",
            "approved explanation section received without rewriting",
            section_id=section.section_id,
            inputs=section.explanation_section_ids,
        )
        add(
            "RESPONSE_SECTION_CREATED",
            "INCLUDED",
            "response section arranged according to the selected format",
            section_id=section.section_id,
            inputs=section.explanation_section_ids,
            outputs=(section.section_id,),
        )
    for reference in draft.evidence_references:
        add(
            "EVIDENCE_REFERENCE_ATTACHED",
            "ATTACHED",
            "approved evidence reference preserved",
            inputs=(reference.source_id,),
            outputs=(reference.reference_id,),
        )
    for limitation in draft.limitations:
        add("LIMITATION_ATTACHED", "ATTACHED", limitation)
    for assumption in draft.assumptions:
        add("ASSUMPTION_ATTACHED", "ATTACHED", assumption)
    for question in draft.clarification_questions:
        add("CLARIFICATION_ATTACHED", "ATTACHED", question)
    add(
        "RESPONSE_VALIDATED",
        integrity.integrity_status,
        "assembled response passed deterministic integrity validation",
        inputs=(integrity.validation_id,),
    )
    add(
        "RESPONSE_ASSEMBLY_COMPLETED",
        response_status,
        "final structured response assembled without adding insurance meaning",
        outputs=(response_id,),
    )

    confidence = min(decision.confidence, explanation.confidence, integrity.confidence)
    if response_status == "ANSWER_WITH_LIMITATIONS":
        confidence = min(confidence, 0.9)
    if response_status == "CLARIFICATION_REQUIRED":
        confidence = min(confidence, 0.75)

    return build_output(
        request_id=assembler_input.request_id,
        response_id=response_id,
        response_status=response_status,
        audience=explanation.audience,
        response_format=assembler_input.response_format,
        direct_answer=draft.direct_answer,
        sections=draft.sections,
        evidence_references=draft.evidence_references,
        limitations=draft.limitations,
        assumptions=draft.assumptions,
        clarification_questions=draft.clarification_questions,
        confidence=confidence,
        response_trace=tuple(trace),
    )
