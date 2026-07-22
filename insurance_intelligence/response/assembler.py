"""Deterministic section assembly for MO-020C.

This module arranges already-approved explanation content.  It does not create
new insurance meaning, retrieve evidence, or alter upstream decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence

from insurance_intelligence.contracts.explanation import ExplanationSection
from insurance_intelligence.contracts.response import (
    EvidenceReference,
    ResponseAssemblerInput,
    ResponseSection,
    build_evidence_reference,
    build_section,
)
from insurance_intelligence.response.registry import ResponseFormatDefinition


class ResponseAssemblyError(ValueError):
    """Raised when approved content cannot be assembled safely."""


EXPLANATION_TO_RESPONSE_SECTION = {
    "DIRECT_ANSWER": "DIRECT_ANSWER",
    "MEANING": "EXPLANATION",
    "CONDITION": "CONDITION",
    "IMPACT": "IMPACT",
    "LIMITATION": "LIMITATION",
    "EVIDENCE_NOTE": "EVIDENCE",
    "CLARIFICATION": "CLARIFICATION",
    "ADVISOR_TALKING_POINT": "ADVISOR_TALKING_POINT",
    "INTERNAL_REVIEW_NOTE": "INTERNAL_NOTE",
}


@dataclass(frozen=True)
class ResponseAssemblyDraft:
    direct_answer: str | None
    sections: tuple[ResponseSection, ...]
    evidence_references: tuple[EvidenceReference, ...]
    limitations: tuple[str, ...]
    assumptions: tuple[str, ...]
    clarification_questions: tuple[str, ...]


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _word_count(text: str) -> int:
    return len(text.split())


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _response_status(decision: str) -> str:
    mapping = {
        "APPROVED": "ANSWER",
        "APPROVED_WITH_LIMITATIONS": "ANSWER_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUIRED",
    }
    try:
        return mapping[decision]
    except KeyError as exc:  # guarded by ResponseAssemblerInput, retained fail-closed
        raise ResponseAssemblyError(f"unsupported assembly decision: {decision}") from exc


def _context_strings(context: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = context.get(key, ())
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value.strip() else ()
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        result: list[str] = []
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ResponseAssemblyError(f"assembly_context[{key!r}] must contain non-empty strings")
            result.append(item)
        return _unique(result)
    raise ResponseAssemblyError(f"assembly_context[{key!r}] must be a string or sequence of strings")


def _locator(context: Mapping[str, object], evidence_id: str) -> str | None:
    locators = context.get("evidence_locators", {})
    if locators is None:
        return None
    if not isinstance(locators, Mapping):
        raise ResponseAssemblyError("assembly_context['evidence_locators'] must be a mapping")
    value = locators.get(evidence_id)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ResponseAssemblyError("evidence locator must be a non-empty string")
    return value


def _label(context: Mapping[str, object], evidence_id: str) -> str:
    labels = context.get("evidence_labels", {})
    if labels is None:
        return f"Approved evidence {evidence_id}"
    if not isinstance(labels, Mapping):
        raise ResponseAssemblyError("assembly_context['evidence_labels'] must be a mapping")
    value = labels.get(evidence_id)
    if value is None:
        return f"Approved evidence {evidence_id}"
    if not isinstance(value, str) or not value.strip():
        raise ResponseAssemblyError("evidence label must be a non-empty string")
    return value


def _section_sort_key(section: ResponseSection, definition: ResponseFormatDefinition) -> tuple[int, str]:
    order = {section_type: index for index, section_type in enumerate(definition.section_order)}
    return (order.get(section.section_type, len(order)), section.section_id)


def _build_references(
    sections: Sequence[ExplanationSection],
    context: Mapping[str, object],
) -> tuple[EvidenceReference, ...]:
    finding_map: dict[str, set[str]] = {}
    for section in sections:
        if section.status != "DRAFTED":
            continue
        for evidence_id in section.evidence_ids:
            finding_map.setdefault(evidence_id, set()).update(section.approved_finding_ids)
    references = [
        build_evidence_reference(
            reference_id=_stable_id("ref", evidence_id),
            reference_type="EVIDENCE",
            source_id=evidence_id,
            label=_label(context, evidence_id),
            locator=_locator(context, evidence_id),
            approved_finding_ids=tuple(sorted(findings)),
        )
        for evidence_id, findings in sorted(finding_map.items())
    ]
    return tuple(references)


def assemble_sections(
    assembler_input: ResponseAssemblerInput,
    format_definition: ResponseFormatDefinition,
) -> ResponseAssemblyDraft:
    """Arrange approved explanation sections according to a selected format."""
    if not isinstance(assembler_input, ResponseAssemblerInput):
        raise ResponseAssemblyError("assembler_input must be a ResponseAssemblerInput")
    if not isinstance(format_definition, ResponseFormatDefinition):
        raise ResponseAssemblyError("format_definition must be a ResponseFormatDefinition")

    explanation = assembler_input.explanation_output
    decision = assembler_input.decision_output
    response_status = _response_status(decision.decision)
    if format_definition.response_format != assembler_input.response_format:
        raise ResponseAssemblyError("format_definition does not match requested response_format")
    if explanation.audience not in format_definition.audiences:
        raise ResponseAssemblyError("format_definition does not support explanation audience")
    if response_status not in format_definition.response_statuses:
        raise ResponseAssemblyError("format_definition does not support mapped response status")

    drafted = tuple(section for section in explanation.sections if section.status == "DRAFTED")
    if not drafted:
        raise ResponseAssemblyError("explanation output contains no drafted sections")

    references = _build_references(drafted, assembler_input.assembly_context)
    reference_by_source = {item.source_id: item.reference_id for item in references}

    response_sections: list[ResponseSection] = []
    direct_candidates: list[str] = []
    clarification_questions: list[str] = []
    limitation_ids: list[str] = []

    for section in drafted:
        try:
            response_type = EXPLANATION_TO_RESPONSE_SECTION[section.section_type]
        except KeyError as exc:
            raise ResponseAssemblyError(f"unsupported explanation section type: {section.section_type}") from exc
        if response_type not in format_definition.allowed_section_types:
            continue
        if _word_count(section.text) > format_definition.max_section_words:
            raise ResponseAssemblyError(f"section exceeds max_section_words: {section.section_id}")

        evidence_reference_ids = tuple(reference_by_source[evidence_id] for evidence_id in section.evidence_ids)
        response_section = build_section(
            section_id=_stable_id("section", assembler_input.request_id, section.section_id, response_type),
            section_type=response_type,
            status="INCLUDED",
            text=section.text,
            explanation_section_ids=(section.section_id,),
            approved_finding_ids=section.approved_finding_ids,
            evidence_reference_ids=evidence_reference_ids,
            limitation_ids=section.limitation_ids,
            clarification_ids=section.clarification_ids,
        )
        response_sections.append(response_section)
        limitation_ids.extend(section.limitation_ids)
        if response_type == "DIRECT_ANSWER":
            direct_candidates.append(section.text)
        if response_type == "CLARIFICATION":
            clarification_questions.append(section.text)

    response_sections.sort(key=lambda item: _section_sort_key(item, format_definition))
    if len(response_sections) > format_definition.max_sections:
        raise ResponseAssemblyError("assembled response exceeds max_sections")

    if format_definition.direct_answer_policy == "REQUIRED":
        if not direct_candidates:
            # Deterministic fallback to the first approved explanatory section; no rewriting.
            candidates = [
                item.text
                for item in response_sections
                if item.section_type in {"EXPLANATION", "IMPACT", "CONDITION", "ADVISOR_TALKING_POINT"}
            ]
            if not candidates:
                raise ResponseAssemblyError("required direct answer is unavailable")
            direct_candidates = [candidates[0]]
        direct_answer: str | None = direct_candidates[0]
        if _word_count(direct_answer) > format_definition.max_direct_answer_words:
            raise ResponseAssemblyError("direct answer exceeds max_direct_answer_words")
    elif format_definition.direct_answer_policy == "OPTIONAL":
        direct_answer = direct_candidates[0] if direct_candidates else None
        if direct_answer is not None and _word_count(direct_answer) > format_definition.max_direct_answer_words:
            raise ResponseAssemblyError("direct answer exceeds max_direct_answer_words")
    else:
        direct_answer = None

    if format_definition.evidence_policy == "REQUIRED" and not references:
        raise ResponseAssemblyError("response format requires evidence references")
    if format_definition.evidence_policy == "FORBIDDEN":
        references = ()
        if any(section.evidence_reference_ids for section in response_sections):
            raise ResponseAssemblyError("response format forbids evidence references")

    limitations = _unique((*explanation.limitations, *_context_strings(assembler_input.assembly_context, "limitations")))
    assumptions = _context_strings(assembler_input.assembly_context, "assumptions")
    clarification_questions = list(_unique(clarification_questions))

    if format_definition.limitation_policy == "ALWAYS" and not limitations:
        raise ResponseAssemblyError("response format requires a limitation")
    if format_definition.limitation_policy == "REQUIRED_WHEN_PRESENT" and limitation_ids and not limitations:
        raise ResponseAssemblyError("limitation IDs are present but limitation text is unavailable")
    if format_definition.limitation_policy == "FORBIDDEN":
        limitations = ()
    if format_definition.assumption_policy == "ALWAYS" and not assumptions:
        raise ResponseAssemblyError("response format requires an assumption")
    if format_definition.assumption_policy == "FORBIDDEN":
        assumptions = ()

    if format_definition.clarification_policy == "REQUIRED":
        if not clarification_questions:
            raise ResponseAssemblyError("response format requires clarification content")
    else:
        if clarification_questions:
            raise ResponseAssemblyError("answer response cannot contain clarification content")

    return ResponseAssemblyDraft(
        direct_answer=direct_answer,
        sections=tuple(response_sections),
        evidence_references=tuple(references),
        limitations=limitations,
        assumptions=assumptions,
        clarification_questions=tuple(clarification_questions),
    )
