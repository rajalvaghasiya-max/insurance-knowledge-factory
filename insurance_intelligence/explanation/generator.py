"""Executable evidence-locked Explanation Generator (MO-019E)."""
from __future__ import annotations

from dataclasses import replace
import hashlib
from typing import Mapping

from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorInput,
    ExplanationGeneratorOutput,
    ExplanationTraceEvent,
    build_output,
    build_trace_event,
)
from insurance_intelligence.contracts.reasoning import Finding
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    TerminologyRegistry,
)
from insurance_intelligence.explanation.templates import render_explanation_templates
from insurance_intelligence.explanation.validator import validate_explanation_fidelity


class ExplanationGenerationError(ValueError):
    """Raised when explanation generation cannot proceed safely."""


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _event(
    *,
    request_id: str,
    sequence: int,
    event_type: str,
    decision: str,
    basis: str,
    section_id: str | None = None,
    input_references: tuple[str, ...] = (),
    output_references: tuple[str, ...] = (),
) -> ExplanationTraceEvent:
    return build_trace_event(
        trace_id=_stable_id("trace", request_id, str(sequence), event_type, section_id or ""),
        sequence=sequence,
        event_type=event_type,
        section_id=section_id,
        decision=decision,
        basis=basis,
        input_references=input_references,
        output_references=output_references,
        order_marker=f"{sequence:04d}:{event_type}",
    )


def _scope(input_value: ExplanationGeneratorInput) -> str:
    raw = input_value.communication_context.get("domain_scope", "GLOBAL")
    value = str(raw).strip().upper()
    return value if value in {"GLOBAL", "HEALTH", "MOTOR", "LIFE", "TRAVEL"} else "GLOBAL"


def _source_terms(findings: Mapping[str, Finding]) -> tuple[str, ...]:
    terms: set[str] = set()
    for finding in findings.values():
        text = " ".join((finding.subject, finding.predicate, finding.object_or_effect, finding.condition))
        for candidate in (
            "admissible claim amount",
            "conditional co-payment",
            "co-payment",
            "insured",
            "policyholder",
        ):
            if candidate in text:
                terms.add(candidate)
    return tuple(sorted(terms))


def generate_explanation(
    *,
    explanation_input: ExplanationGeneratorInput,
    findings_by_id: Mapping[str, Finding],
    style_registry: ExplanationStyleRegistry,
    terminology_registry: TerminologyRegistry | None = None,
) -> ExplanationGeneratorOutput:
    """Generate and fidelity-check a deterministic explanation draft.

    The generator is presentation-only: it consumes an already approved Decision
    Gate output and never retrieves evidence, performs reasoning, or changes the
    approved decision scope.
    """
    if not isinstance(explanation_input, ExplanationGeneratorInput):
        raise ExplanationGenerationError("explanation_input must be validated")
    if not isinstance(style_registry, ExplanationStyleRegistry):
        raise ExplanationGenerationError("style_registry must be an ExplanationStyleRegistry")
    if terminology_registry is not None and not isinstance(terminology_registry, TerminologyRegistry):
        raise ExplanationGenerationError("terminology_registry must be a TerminologyRegistry")
    if any(not isinstance(key, str) or not isinstance(value, Finding) for key, value in findings_by_id.items()):
        raise ExplanationGenerationError("findings_by_id must map string IDs to Finding values")
    if any(key != value.finding_id for key, value in findings_by_id.items()):
        raise ExplanationGenerationError("finding map keys must match finding IDs")

    eligible_styles = style_registry.eligible_styles(
        audience=explanation_input.audience,
        reading_level=explanation_input.reading_level,
        explanation_mode=explanation_input.explanation_mode,
    )
    if not eligible_styles:
        raise ExplanationGenerationError("no eligible explanation style is registered")
    style = eligible_styles[0]

    terms = ()
    if terminology_registry is not None:
        terms = terminology_registry.eligible_terms(
            source_terms=_source_terms(findings_by_id),
            audience=explanation_input.audience,
            reading_level=explanation_input.reading_level,
            explanation_mode=explanation_input.explanation_mode,
            scope=_scope(explanation_input),
        )

    trace: list[ExplanationTraceEvent] = []
    seq = 1
    trace.append(_event(
        request_id=explanation_input.request_id,
        sequence=seq,
        event_type="EXPLANATION_STARTED",
        decision="STARTED",
        basis="Validated explanation request received.",
        input_references=(explanation_input.decision_output.decision_id,),
    ))
    seq += 1
    trace.append(_event(
        request_id=explanation_input.request_id,
        sequence=seq,
        event_type="INPUT_VALIDATED",
        decision="VALID",
        basis="Audience, reading level, mode, and Decision Gate eligibility are valid.",
        input_references=(style.style_id, style.style_version),
    ))
    seq += 1
    packet_event = "CLARIFICATION_RECEIVED" if explanation_input.decision_output.decision == "CLARIFICATION_REQUIRED" else "APPROVED_PACKET_RECEIVED"
    refs = tuple(
        item.clarification_id for item in explanation_input.decision_output.clarifications
    ) if packet_event == "CLARIFICATION_RECEIVED" else tuple(
        explanation_input.decision_output.response_packet.approved_finding_ids  # type: ignore[union-attr]
    )
    trace.append(_event(
        request_id=explanation_input.request_id,
        sequence=seq,
        event_type=packet_event,
        decision="ACCEPTED",
        basis="Only Decision Gate-approved communication scope is eligible for rendering.",
        input_references=tuple(sorted(refs)),
    ))
    seq += 1

    rendered = render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id=findings_by_id,
        style=style,
        terminology=terms,
    )
    for section in rendered.sections:
        trace.append(_event(
            request_id=explanation_input.request_id,
            sequence=seq,
            event_type="SECTION_CREATED",
            section_id=section.section_id,
            decision="DRAFTED",
            basis=f"Deterministic template rendered {section.section_type} section.",
            input_references=section.approved_finding_ids + section.clarification_ids,
            output_references=(section.section_id,),
        ))
        seq += 1
    for substitution in rendered.terminology_substitutions:
        trace.append(_event(
            request_id=explanation_input.request_id,
            sequence=seq,
            event_type="TERMINOLOGY_APPLIED",
            decision="APPLIED",
            basis=f"Registered {substitution.action} terminology substitution applied.",
            input_references=(substitution.source_term,),
            output_references=(substitution.substitution_id,),
        ))
        seq += 1

    validation = validate_explanation_fidelity(
        explanation_input=explanation_input,
        sections=rendered.sections,
        findings_by_id=findings_by_id,
        terminology_substitutions=rendered.terminology_substitutions,
    )
    trace.append(_event(
        request_id=explanation_input.request_id,
        sequence=seq,
        event_type="FIDELITY_CHECKED",
        decision=validation.validation_status,
        basis="Draft compared with approved findings, evidence, conditions, limitations, and decision scope.",
        input_references=tuple(check.check_id for check in validation.checks),
        output_references=tuple(section.section_id for section in rendered.sections),
    ))
    seq += 1

    if validation.fidelity_status == "FAILED":
        withheld = tuple(replace(section, status="WITHHELD") for section in rendered.sections)
        for section in withheld:
            trace.append(_event(
                request_id=explanation_input.request_id,
                sequence=seq,
                event_type="SECTION_WITHHELD",
                section_id=section.section_id,
                decision="WITHHELD",
                basis="Fidelity validation failed; content is not eligible for communication.",
                output_references=(section.section_id,),
            ))
            seq += 1
        explanation_status = "WITHHELD"
        sections = withheld
        confidence = 0.0
    elif explanation_input.decision_output.decision == "CLARIFICATION_REQUIRED":
        explanation_status = "CLARIFICATION_DRAFTED"
        sections = rendered.sections
        confidence = validation.confidence
    elif validation.fidelity_status == "VERIFIED_WITH_LIMITATIONS":
        explanation_status = "DRAFTED_WITH_LIMITATIONS"
        sections = rendered.sections
        confidence = validation.confidence
    else:
        explanation_status = "DRAFTED"
        sections = rendered.sections
        confidence = validation.confidence

    trace.append(_event(
        request_id=explanation_input.request_id,
        sequence=seq,
        event_type="EXPLANATION_COMPLETED",
        decision=explanation_status,
        basis="Explanation generation completed without changing approved meaning.",
        output_references=tuple(section.section_id for section in sections),
    ))

    explanation_id = _stable_id(
        "explanation",
        explanation_input.request_id,
        explanation_input.decision_output.decision_id,
        explanation_input.audience,
        explanation_input.reading_level,
        explanation_input.explanation_mode,
        style.style_id,
        style.style_version,
        *rendered.template_ids,
    )
    return build_output(
        request_id=explanation_input.request_id,
        explanation_id=explanation_id,
        audience=explanation_input.audience,
        reading_level=explanation_input.reading_level,
        explanation_mode=explanation_input.explanation_mode,
        sections=sections,
        terminology_substitutions=rendered.terminology_substitutions,
        fidelity_checks=validation.checks,
        fidelity_status=validation.fidelity_status,
        limitations=validation.limitations,
        explanation_status=explanation_status,
        confidence=confidence,
        explanation_trace=tuple(trace),
    )
