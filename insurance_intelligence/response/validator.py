"""Deterministic integrity validation for assembled responses (MO-020D).

The validator never rewrites response content. It compares an assembly draft
with the approved Decision Gate packet, the fidelity-validated explanation,
and the selected response-format definition, then fails closed on divergence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence

from insurance_intelligence.contracts.response import ResponseAssemblerInput, ResponseSection
from insurance_intelligence.response.assembler import (
    EXPLANATION_TO_RESPONSE_SECTION,
    ResponseAssemblyDraft,
)
from insurance_intelligence.response.registry import ResponseFormatDefinition

INTEGRITY_STATUSES = frozenset(
    {
        "VERIFIED",
        "VERIFIED_WITH_LIMITATIONS",
        "FAILED_DECISION_MISMATCH",
        "FAILED_EXPLANATION_MISMATCH",
        "FAILED_SECTION_SCOPE",
        "FAILED_EVIDENCE_REFERENCE",
        "FAILED_LIMITATION_FIDELITY",
        "FAILED_ASSUMPTION_FIDELITY",
        "FAILED_CLARIFICATION_SCOPE",
        "FAILED_UNSUPPORTED_CONTENT",
        "FAILED_FORMAT_LIMIT",
        "FAILED_ORDERING",
    }
)
CHECK_STATUSES = frozenset({"PASSED", "FAILED", "WARNING"})


class ResponseIntegrityError(ValueError):
    """Raised when response-integrity validation inputs are invalid."""


@dataclass(frozen=True)
class ResponseIntegrityCheck:
    check_id: str
    check_type: str
    status: str
    section_id: str | None
    description: str
    source_references: tuple[str, ...]


@dataclass(frozen=True)
class ResponseIntegrityResult:
    validation_id: str
    request_id: str
    integrity_status: str
    checks: tuple[ResponseIntegrityCheck, ...]
    limitations: tuple[str, ...]
    confidence: float

    @property
    def verified(self) -> bool:
        return self.integrity_status in {"VERIFIED", "VERIFIED_WITH_LIMITATIONS"}


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))


def _word_count(text: str) -> int:
    return len(text.split())


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
                raise ResponseIntegrityError(f"assembly_context[{key!r}] must contain non-empty strings")
            result.append(item)
        return _unique(result)
    raise ResponseIntegrityError(f"assembly_context[{key!r}] must be a string or sequence of strings")


def _response_status(decision: str) -> str:
    mapping = {
        "APPROVED": "ANSWER",
        "APPROVED_WITH_LIMITATIONS": "ANSWER_WITH_LIMITATIONS",
        "CLARIFICATION_REQUIRED": "CLARIFICATION_REQUIRED",
    }
    try:
        return mapping[decision]
    except KeyError as exc:
        raise ResponseIntegrityError(f"unsupported decision for response validation: {decision}") from exc


def _check(
    *,
    request_id: str,
    check_type: str,
    status: str,
    description: str,
    section_id: str | None = None,
    source_references: Sequence[str] = (),
) -> ResponseIntegrityCheck:
    if status not in CHECK_STATUSES:
        raise ResponseIntegrityError(f"unsupported check status: {status}")
    refs = tuple(sorted(_unique(source_references)))
    return ResponseIntegrityCheck(
        check_id=_stable_id("response-check", request_id, check_type, section_id or "", status, *refs),
        check_type=check_type,
        status=status,
        section_id=section_id,
        description=description,
        source_references=refs,
    )


def _expected_section_order(
    sections: Sequence[ResponseSection], definition: ResponseFormatDefinition
) -> tuple[str, ...]:
    order = {section_type: index for index, section_type in enumerate(definition.section_order)}
    return tuple(
        item.section_id
        for item in sorted(sections, key=lambda item: (order.get(item.section_type, len(order)), item.section_id))
    )


def _failure_status(checks: Sequence[ResponseIntegrityCheck]) -> str | None:
    precedence = (
        ("DECISION", "FAILED_DECISION_MISMATCH"),
        ("EXPLANATION", "FAILED_EXPLANATION_MISMATCH"),
        ("SECTION_SCOPE", "FAILED_SECTION_SCOPE"),
        ("EVIDENCE", "FAILED_EVIDENCE_REFERENCE"),
        ("LIMITATION", "FAILED_LIMITATION_FIDELITY"),
        ("ASSUMPTION", "FAILED_ASSUMPTION_FIDELITY"),
        ("CLARIFICATION", "FAILED_CLARIFICATION_SCOPE"),
        ("UNSUPPORTED_CONTENT", "FAILED_UNSUPPORTED_CONTENT"),
        ("FORMAT_LIMIT", "FAILED_FORMAT_LIMIT"),
        ("ORDERING", "FAILED_ORDERING"),
    )
    failed_types = {item.check_type for item in checks if item.status == "FAILED"}
    for check_type, result in precedence:
        if check_type in failed_types:
            return result
    return None


def validate_response_draft(
    assembler_input: ResponseAssemblerInput,
    format_definition: ResponseFormatDefinition,
    draft: ResponseAssemblyDraft,
) -> ResponseIntegrityResult:
    """Validate an assembled response without modifying or rewriting it."""
    if not isinstance(assembler_input, ResponseAssemblerInput):
        raise ResponseIntegrityError("assembler_input must be a ResponseAssemblerInput")
    if not isinstance(format_definition, ResponseFormatDefinition):
        raise ResponseIntegrityError("format_definition must be a ResponseFormatDefinition")
    if not isinstance(draft, ResponseAssemblyDraft):
        raise ResponseIntegrityError("draft must be a ResponseAssemblyDraft")

    request_id = assembler_input.request_id
    decision = assembler_input.decision_output
    explanation = assembler_input.explanation_output
    expected_status = _response_status(decision.decision)
    checks: list[ResponseIntegrityCheck] = []

    format_matches = (
        format_definition.response_format == assembler_input.response_format
        and explanation.audience in format_definition.audiences
        and expected_status in format_definition.response_statuses
    )
    checks.append(
        _check(
            request_id=request_id,
            check_type="DECISION",
            status="PASSED" if format_matches else "FAILED",
            description="response format matches the approved decision and audience",
            source_references=(decision.decision_id, explanation.explanation_id, format_definition.format_id),
        )
    )

    drafted_sections = {item.section_id: item for item in explanation.sections if item.status == "DRAFTED"}
    response_packet = decision.response_packet
    approved_findings = set(response_packet.approved_finding_ids) if response_packet is not None else set()
    approved_evidence = set(response_packet.approved_evidence_ids) if response_packet is not None else set()
    known_clarifications = {item.clarification_id for item in decision.clarifications}
    reference_by_id = {item.reference_id: item for item in draft.evidence_references}

    explanation_ok = bool(drafted_sections)
    checks.append(
        _check(
            request_id=request_id,
            check_type="EXPLANATION",
            status="PASSED" if explanation_ok else "FAILED",
            description="assembled response is derived from drafted explanation sections",
            source_references=tuple(sorted(drafted_sections)),
        )
    )

    for section in draft.sections:
        source_ids = section.explanation_section_ids
        sources = [drafted_sections.get(item) for item in source_ids]
        known_sources = bool(source_ids) and all(item is not None for item in sources)
        expected_types = {
            EXPLANATION_TO_RESPONSE_SECTION[item.section_type]  # type: ignore[union-attr]
            for item in sources
            if item is not None and item.section_type in EXPLANATION_TO_RESPONSE_SECTION
        }
        exact_text = known_sources and section.text in {item.text for item in sources if item is not None}
        scope_ok = (
            section.status == "INCLUDED"
            and known_sources
            and len(expected_types) == 1
            and section.section_type in expected_types
            and section.section_type in format_definition.allowed_section_types
            and set(section.approved_finding_ids) <= approved_findings
        )
        checks.append(
            _check(
                request_id=request_id,
                check_type="SECTION_SCOPE",
                status="PASSED" if scope_ok else "FAILED",
                description="response section remains within approved explanation and finding scope",
                section_id=section.section_id,
                source_references=source_ids,
            )
        )
        checks.append(
            _check(
                request_id=request_id,
                check_type="UNSUPPORTED_CONTENT",
                status="PASSED" if exact_text else "FAILED",
                description="response section text exactly preserves approved explanation content",
                section_id=section.section_id,
                source_references=source_ids,
            )
        )

        source_evidence = {
            evidence_id
            for item in sources
            if item is not None
            for evidence_id in item.evidence_ids
        }
        section_refs = [reference_by_id.get(item) for item in section.evidence_reference_ids]
        evidence_ok = all(item is not None for item in section_refs)
        resolved_sources = {item.source_id for item in section_refs if item is not None}
        if source_evidence:
            evidence_ok = evidence_ok and resolved_sources == source_evidence
        else:
            evidence_ok = evidence_ok and not resolved_sources
        evidence_ok = evidence_ok and resolved_sources <= approved_evidence
        checks.append(
            _check(
                request_id=request_id,
                check_type="EVIDENCE",
                status="PASSED" if evidence_ok else "FAILED",
                description="section evidence references match approved explanation evidence",
                section_id=section.section_id,
                source_references=tuple(sorted(source_evidence)),
            )
        )

    all_reference_sources = {item.source_id for item in draft.evidence_references}
    unique_reference_ids = len(reference_by_id) == len(draft.evidence_references)
    global_evidence_ok = unique_reference_ids and all_reference_sources <= approved_evidence
    if expected_status == "CLARIFICATION_REQUIRED":
        global_evidence_ok = global_evidence_ok and not draft.evidence_references
    checks.append(
        _check(
            request_id=request_id,
            check_type="EVIDENCE",
            status="PASSED" if global_evidence_ok else "FAILED",
            description="global evidence references are unique and approved",
            source_references=tuple(sorted(all_reference_sources)),
        )
    )

    expected_limitations = set(explanation.limitations) | set(_context_strings(assembler_input.assembly_context, "limitations"))
    limitation_ok = expected_limitations <= set(draft.limitations)
    if expected_status == "ANSWER_WITH_LIMITATIONS":
        limitation_ok = limitation_ok and bool(draft.limitations)
    checks.append(
        _check(
            request_id=request_id,
            check_type="LIMITATION",
            status="PASSED" if limitation_ok else "FAILED",
            description="all approved limitations remain visible",
            source_references=tuple(sorted(expected_limitations)),
        )
    )

    expected_assumptions = set(_context_strings(assembler_input.assembly_context, "assumptions"))
    assumption_ok = expected_assumptions <= set(draft.assumptions)
    checks.append(
        _check(
            request_id=request_id,
            check_type="ASSUMPTION",
            status="PASSED" if assumption_ok else "FAILED",
            description="all approved assumptions remain visible",
            source_references=tuple(sorted(expected_assumptions)),
        )
    )

    clarification_sections = [item for item in draft.sections if item.section_type == "CLARIFICATION"]
    clarification_ids = {item for section in clarification_sections for item in section.clarification_ids}
    if expected_status == "CLARIFICATION_REQUIRED":
        clarification_ok = (
            draft.direct_answer is None
            and bool(draft.clarification_questions)
            and bool(clarification_sections)
            and len(clarification_sections) == len(draft.sections)
            and clarification_ids <= known_clarifications
            and not draft.evidence_references
        )
    else:
        clarification_ok = not clarification_sections and not draft.clarification_questions
    checks.append(
        _check(
            request_id=request_id,
            check_type="CLARIFICATION",
            status="PASSED" if clarification_ok else "FAILED",
            description="answer and clarification scopes remain mutually exclusive",
            source_references=tuple(sorted(clarification_ids)),
        )
    )

    direct_texts = {item.text for item in draft.sections if item.section_type == "DIRECT_ANSWER"}
    approved_texts = {item.text for item in drafted_sections.values()}
    if format_definition.direct_answer_policy == "REQUIRED":
        direct_ok = draft.direct_answer is not None and draft.direct_answer in approved_texts
    elif format_definition.direct_answer_policy == "OPTIONAL":
        direct_ok = draft.direct_answer is None or draft.direct_answer in approved_texts
    else:
        direct_ok = draft.direct_answer is None and not direct_texts
    checks.append(
        _check(
            request_id=request_id,
            check_type="UNSUPPORTED_CONTENT",
            status="PASSED" if direct_ok else "FAILED",
            description="direct answer is copied from approved explanation content",
            source_references=tuple(sorted(direct_texts)),
        )
    )

    format_ok = (
        len(draft.sections) <= format_definition.max_sections
        and all(_word_count(item.text) <= format_definition.max_section_words for item in draft.sections)
        and (
            draft.direct_answer is None
            or _word_count(draft.direct_answer) <= format_definition.max_direct_answer_words
        )
    )
    checks.append(
        _check(
            request_id=request_id,
            check_type="FORMAT_LIMIT",
            status="PASSED" if format_ok else "FAILED",
            description="response respects configured section and word limits",
            source_references=(format_definition.format_id,),
        )
    )

    actual_order = tuple(item.section_id for item in draft.sections)
    expected_order = _expected_section_order(draft.sections, format_definition)
    ordering_ok = actual_order == expected_order and len(actual_order) == len(set(actual_order))
    checks.append(
        _check(
            request_id=request_id,
            check_type="ORDERING",
            status="PASSED" if ordering_ok else "FAILED",
            description="response section IDs are unique and follow deterministic format order",
            source_references=actual_order,
        )
    )

    failure = _failure_status(checks)
    limitations = _unique((*draft.limitations, *explanation.limitations))
    if failure is not None:
        status = failure
        confidence = 0.0
    elif limitations:
        status = "VERIFIED_WITH_LIMITATIONS"
        confidence = min(assembler_input.decision_output.confidence, explanation.confidence, 0.9)
    else:
        status = "VERIFIED"
        confidence = min(assembler_input.decision_output.confidence, explanation.confidence)

    return ResponseIntegrityResult(
        validation_id=_stable_id(
            "response-validation",
            request_id,
            format_definition.format_id,
            status,
            *(item.check_id for item in checks),
        ),
        request_id=request_id,
        integrity_status=status,
        checks=tuple(checks),
        limitations=limitations,
        confidence=round(float(confidence), 6),
    )
