"""Executable contracts for the evidence-locked Explanation Generator (MO-019)."""
from __future__ import annotations

from dataclasses import dataclass
from string import Formatter
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import DecisionGateOutput
from insurance_intelligence.contracts.education_publication import (
    EducationPublicationRecord,
    validate_education_publication_record,
)

SUPPORTED_CONTRACT_VERSION = "1.0"
AUDIENCES = frozenset({"CUSTOMER", "ADVISOR", "INTERNAL_REVIEWER"})
READING_LEVELS = frozenset({"SIMPLE", "STANDARD", "TECHNICAL"})
EXPLANATION_MODES = frozenset(
    {
        "PLAIN_LANGUAGE",
        "DETAILED",
        "ADVISOR_TALKING_POINTS",
        "CLAUSE_MEANING",
        "LIMITATION_NOTICE",
        "CLARIFICATION_REQUEST",
    }
)
SECTION_TYPES = frozenset(
    {
        "DIRECT_ANSWER",
        "MEANING",
        "CONDITION",
        "IMPACT",
        "LIMITATION",
        "EVIDENCE_NOTE",
        "CLARIFICATION",
        "ADVISOR_TALKING_POINT",
        "INTERNAL_REVIEW_NOTE",
        "EDUCATION",
        "EXAMPLE",
        "PRACTICAL_ILLUSTRATION",
    }
)
SECTION_STATUSES = frozenset({"DRAFTED", "WITHHELD", "REQUIRES_REVIEW"})
TERMINOLOGY_ACTIONS = frozenset({"PRESERVE", "SIMPLIFY", "EXPAND", "DEFINE"})
FIDELITY_CHECK_TYPES = frozenset(
    {
        "APPROVED_FINDING_COVERAGE",
        "EVIDENCE_REFERENCE_PRESERVATION",
        "CONDITION_PRESERVATION",
        "CONDITIONAL_SEMANTIC_INTEGRITY",
        "LIMITATION_PRESERVATION",
        "SCOPE_PRESERVATION",
        "NO_NEW_FACTS",
        "NO_NEW_REASONING",
        "NO_RECOMMENDATION",
        "NO_WITHHELD_CONTENT",
        "TERMINOLOGY_ACCURACY",
        "EDUCATION_PUBLICATION_FIDELITY",
        "PRACTICAL_ILLUSTRATION_FIDELITY",
    }
)
FIDELITY_CHECK_STATUSES = frozenset({"PASSED", "FAILED", "NOT_APPLICABLE", "REQUIRES_REVIEW"})
FIDELITY_STATUSES = frozenset({"VERIFIED", "VERIFIED_WITH_LIMITATIONS", "FAILED", "REQUIRES_REVIEW"})
EXPLANATION_STATUSES = frozenset(
    {
        "DRAFTED",
        "DRAFTED_WITH_LIMITATIONS",
        "CLARIFICATION_DRAFTED",
        "WITHHELD",
        "REQUIRES_REVIEW",
        "INVALID_INPUT",
    }
)
TRACE_EVENT_TYPES = frozenset(
    {
        "EXPLANATION_STARTED",
        "INPUT_VALIDATED",
        "APPROVED_PACKET_RECEIVED",
        "CLARIFICATION_RECEIVED",
        "SECTION_CREATED",
        "TERMINOLOGY_APPLIED",
        "FIDELITY_CHECKED",
        "SECTION_WITHHELD",
        "EXPLANATION_COMPLETED",
        "EDUCATION_PUBLICATION_RECEIVED",
    }
)


class ExplanationContractError(ValueError):
    """Raised when an Explanation Generator contract is invalid."""


def _require_nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExplanationContractError(f"{label} must be a non-empty string")
    return value


def _require_member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise ExplanationContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _require_bounded_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExplanationContractError(f"{label} must be a number")
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ExplanationContractError(f"{label} must be between 0 and 1; got {numeric}")
    return numeric


def _require_unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_require_nonempty_str(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise ExplanationContractError(f"{label} values must be unique")
    return result


_ALLOWED_ILLUSTRATION_FIELDS = frozenset(
    {
        "related_condition",
        "unrelated_condition",
        "before_probe_value",
        "after_probe_value",
        "duration_value",
        "duration_unit",
        "duration_unit_lower",
    }
)


@dataclass(frozen=True)
class PracticalIllustrationProfile:
    profile_id: str
    concept_id: str
    duration_unit: str
    before_probe_value: int
    after_probe_value: int
    related_condition: str
    unrelated_condition: str
    during_wait_template: str
    unrelated_condition_template: str
    after_wait_template: str
    boundary_text: str


def _validated_illustration_template(value: object, label: str) -> str:
    text = _require_nonempty_str(value, label)
    fields = {
        field_name
        for _, field_name, _, _ in Formatter().parse(text)
        if field_name is not None
    }
    unknown = fields - _ALLOWED_ILLUSTRATION_FIELDS
    if unknown:
        raise ExplanationContractError(
            f"{label} contains unsupported placeholders: {sorted(unknown)}"
        )
    return text


def build_practical_illustration_profile(
    *,
    profile_id: str,
    concept_id: str,
    duration_unit: str,
    before_probe_value: int,
    after_probe_value: int,
    related_condition: str,
    unrelated_condition: str,
    during_wait_template: str,
    unrelated_condition_template: str,
    after_wait_template: str,
    boundary_text: str,
) -> PracticalIllustrationProfile:
    if isinstance(before_probe_value, bool) or not isinstance(before_probe_value, int) or before_probe_value < 1:
        raise ExplanationContractError("before_probe_value must be a positive integer")
    if isinstance(after_probe_value, bool) or not isinstance(after_probe_value, int) or after_probe_value < 1:
        raise ExplanationContractError("after_probe_value must be a positive integer")
    if before_probe_value >= after_probe_value:
        raise ExplanationContractError("before_probe_value must be less than after_probe_value")
    return PracticalIllustrationProfile(
        profile_id=_require_nonempty_str(profile_id, "profile_id"),
        concept_id=_require_nonempty_str(concept_id, "concept_id"),
        duration_unit=_require_nonempty_str(duration_unit, "duration_unit").upper(),
        before_probe_value=before_probe_value,
        after_probe_value=after_probe_value,
        related_condition=_require_nonempty_str(related_condition, "related_condition"),
        unrelated_condition=_require_nonempty_str(unrelated_condition, "unrelated_condition"),
        during_wait_template=_validated_illustration_template(during_wait_template, "during_wait_template"),
        unrelated_condition_template=_validated_illustration_template(unrelated_condition_template, "unrelated_condition_template"),
        after_wait_template=_validated_illustration_template(after_wait_template, "after_wait_template"),
        boundary_text=_validated_illustration_template(boundary_text, "boundary_text"),
    )


@dataclass(frozen=True)
class ExplanationGeneratorInput:
    contract_version: str
    request_id: str
    decision_output: DecisionGateOutput
    audience: str
    reading_level: str
    explanation_mode: str
    communication_context: Mapping[str, object]
    education_publications: tuple[EducationPublicationRecord, ...] = ()
    practical_illustration_profiles: tuple[PracticalIllustrationProfile, ...] = ()


def build_input(
    *,
    request_id: str,
    decision_output: DecisionGateOutput,
    audience: str = "CUSTOMER",
    reading_level: str = "SIMPLE",
    explanation_mode: str = "PLAIN_LANGUAGE",
    communication_context: Mapping[str, object] | None = None,
    education_publications: Sequence[EducationPublicationRecord] = (),
    practical_illustration_profiles: Sequence[PracticalIllustrationProfile] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> ExplanationGeneratorInput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ExplanationContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if not isinstance(decision_output, DecisionGateOutput):
        raise ExplanationContractError("decision_output must be a validated DecisionGateOutput")
    validated_request_id = _require_nonempty_str(request_id, "request_id")
    if decision_output.request_id != validated_request_id:
        raise ExplanationContractError("request_id must match decision_output")
    validated_mode = _require_member(explanation_mode, EXPLANATION_MODES, "explanation_mode")
    if decision_output.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        if decision_output.response_packet is None:
            raise ExplanationContractError("approved decision_output requires an approved response packet")
        if validated_mode == "CLARIFICATION_REQUEST":
            raise ExplanationContractError("approved decisions cannot use clarification-request mode")
    elif decision_output.decision == "CLARIFICATION_REQUIRED":
        if validated_mode != "CLARIFICATION_REQUEST":
            raise ExplanationContractError("clarification decisions require clarification-request mode")
    else:
        raise ExplanationContractError("decision_output is not eligible for explanation generation")
    publications = tuple(education_publications)
    if any(not isinstance(item, EducationPublicationRecord) for item in publications):
        raise ExplanationContractError(
            "education_publications must contain EducationPublicationRecord values"
        )
    publication_ids = [item.publication_id for item in publications]
    if len(publication_ids) != len(set(publication_ids)):
        raise ExplanationContractError("education publication IDs must be unique")
    try:
        publications = tuple(
            validate_education_publication_record(item) for item in publications
        )
    except Exception as exc:
        raise ExplanationContractError(str(exc)) from exc
    profiles = tuple(practical_illustration_profiles)
    if any(not isinstance(item, PracticalIllustrationProfile) for item in profiles):
        raise ExplanationContractError(
            "practical_illustration_profiles must contain PracticalIllustrationProfile values"
        )
    profile_ids = [item.profile_id for item in profiles]
    if len(profile_ids) != len(set(profile_ids)):
        raise ExplanationContractError("practical illustration profile IDs must be unique")
    return ExplanationGeneratorInput(
        contract_version=contract_version,
        request_id=validated_request_id,
        decision_output=decision_output,
        audience=_require_member(audience, AUDIENCES, "audience"),
        reading_level=_require_member(reading_level, READING_LEVELS, "reading_level"),
        explanation_mode=validated_mode,
        communication_context=dict(communication_context or {}),
        education_publications=publications,
        practical_illustration_profiles=profiles,
    )


@dataclass(frozen=True)
class ExplanationSection:
    section_id: str
    section_type: str
    status: str
    text: str
    approved_finding_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]
    education_publication_ids: tuple[str, ...] = ()


def build_section(
    *,
    section_id: str,
    section_type: str,
    status: str,
    text: str,
    approved_finding_ids: Sequence[str] = (),
    evidence_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
    education_publication_ids: Sequence[str] = (),
) -> ExplanationSection:
    validated_status = _require_member(status, SECTION_STATUSES, "section.status")
    validated_type = _require_member(section_type, SECTION_TYPES, "section.section_type")
    findings = _require_unique(approved_finding_ids, "section.approved_finding_ids")
    evidence = _require_unique(evidence_ids, "section.evidence_ids")
    clarifications = _require_unique(clarification_ids, "section.clarification_ids")
    education_ids = _require_unique(
        education_publication_ids, "section.education_publication_ids"
    )
    if validated_status == "DRAFTED" and findings and not evidence:
        raise ExplanationContractError("drafted finding-backed sections must preserve evidence IDs")
    if validated_type == "CLARIFICATION" and not clarifications:
        raise ExplanationContractError("clarification sections must reference clarification IDs")
    if validated_type in {"EDUCATION", "EXAMPLE"}:
        if not education_ids:
            raise ExplanationContractError(
                "education/example sections must reference education publication IDs"
            )
        if findings or evidence or clarifications:
            raise ExplanationContractError(
                "education/example sections cannot reference findings, product evidence, or clarifications"
            )
    elif validated_type == "PRACTICAL_ILLUSTRATION":
        if not education_ids or not findings or not evidence:
            raise ExplanationContractError(
                "practical illustration sections require education, finding, and evidence lineage"
            )
        if clarifications:
            raise ExplanationContractError(
                "practical illustration sections cannot reference clarifications"
            )
    elif education_ids:
        raise ExplanationContractError(
            "only education/example/practical-illustration sections may reference education publication IDs"
        )
    return ExplanationSection(
        section_id=_require_nonempty_str(section_id, "section.section_id"),
        section_type=validated_type,
        status=validated_status,
        text=_require_nonempty_str(text, "section.text"),
        approved_finding_ids=findings,
        evidence_ids=evidence,
        limitation_ids=_require_unique(limitation_ids, "section.limitation_ids"),
        clarification_ids=clarifications,
        education_publication_ids=education_ids,
    )


@dataclass(frozen=True)
class TerminologySubstitution:
    substitution_id: str
    source_term: str
    rendered_term: str
    action: str
    approved_finding_ids: tuple[str, ...]
    meaning_preserved: bool


def build_terminology_substitution(
    *,
    substitution_id: str,
    source_term: str,
    rendered_term: str,
    action: str,
    approved_finding_ids: Sequence[str] = (),
    meaning_preserved: bool = True,
) -> TerminologySubstitution:
    if not isinstance(meaning_preserved, bool):
        raise ExplanationContractError("terminology.meaning_preserved must be boolean")
    return TerminologySubstitution(
        substitution_id=_require_nonempty_str(substitution_id, "terminology.substitution_id"),
        source_term=_require_nonempty_str(source_term, "terminology.source_term"),
        rendered_term=_require_nonempty_str(rendered_term, "terminology.rendered_term"),
        action=_require_member(action, TERMINOLOGY_ACTIONS, "terminology.action"),
        approved_finding_ids=_require_unique(approved_finding_ids, "terminology.approved_finding_ids"),
        meaning_preserved=meaning_preserved,
    )


@dataclass(frozen=True)
class FidelityCheck:
    check_id: str
    check_type: str
    status: str
    source_references: tuple[str, ...]
    section_ids: tuple[str, ...]
    description: str


def build_fidelity_check(
    *,
    check_id: str,
    check_type: str,
    status: str,
    description: str,
    source_references: Sequence[str] = (),
    section_ids: Sequence[str] = (),
) -> FidelityCheck:
    return FidelityCheck(
        check_id=_require_nonempty_str(check_id, "fidelity_check.check_id"),
        check_type=_require_member(check_type, FIDELITY_CHECK_TYPES, "fidelity_check.check_type"),
        status=_require_member(status, FIDELITY_CHECK_STATUSES, "fidelity_check.status"),
        source_references=_require_unique(source_references, "fidelity_check.source_references"),
        section_ids=_require_unique(section_ids, "fidelity_check.section_ids"),
        description=_require_nonempty_str(description, "fidelity_check.description"),
    )


@dataclass(frozen=True)
class ExplanationTraceEvent:
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
) -> ExplanationTraceEvent:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise ExplanationContractError("trace.sequence must be a positive integer")
    if section_id is not None:
        _require_nonempty_str(section_id, "trace.section_id")
    return ExplanationTraceEvent(
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
class ExplanationGeneratorOutput:
    contract_version: str
    request_id: str
    explanation_id: str
    audience: str
    reading_level: str
    explanation_mode: str
    sections: tuple[ExplanationSection, ...]
    terminology_substitutions: tuple[TerminologySubstitution, ...]
    fidelity_checks: tuple[FidelityCheck, ...]
    fidelity_status: str
    limitations: tuple[str, ...]
    explanation_status: str
    confidence: float
    explanation_trace: tuple[ExplanationTraceEvent, ...]


def build_output(
    *,
    request_id: str,
    explanation_id: str,
    audience: str,
    reading_level: str,
    explanation_mode: str,
    sections: Sequence[ExplanationSection] = (),
    terminology_substitutions: Sequence[TerminologySubstitution] = (),
    fidelity_checks: Sequence[FidelityCheck] = (),
    fidelity_status: str,
    limitations: Sequence[str] = (),
    explanation_status: str,
    confidence: float = 0.0,
    explanation_trace: Sequence[ExplanationTraceEvent] = (),
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> ExplanationGeneratorOutput:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ExplanationContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    output = ExplanationGeneratorOutput(
        contract_version=contract_version,
        request_id=_require_nonempty_str(request_id, "request_id"),
        explanation_id=_require_nonempty_str(explanation_id, "explanation_id"),
        audience=_require_member(audience, AUDIENCES, "audience"),
        reading_level=_require_member(reading_level, READING_LEVELS, "reading_level"),
        explanation_mode=_require_member(explanation_mode, EXPLANATION_MODES, "explanation_mode"),
        sections=tuple(sections),
        terminology_substitutions=tuple(terminology_substitutions),
        fidelity_checks=tuple(fidelity_checks),
        fidelity_status=_require_member(fidelity_status, FIDELITY_STATUSES, "fidelity_status"),
        limitations=tuple(_require_nonempty_str(value, "limitations[]") for value in limitations),
        explanation_status=_require_member(explanation_status, EXPLANATION_STATUSES, "explanation_status"),
        confidence=_require_bounded_float(confidence, "confidence"),
        explanation_trace=tuple(explanation_trace),
    )
    return validate_output(output)


def validate_output(output: ExplanationGeneratorOutput) -> ExplanationGeneratorOutput:
    if not isinstance(output, ExplanationGeneratorOutput):
        raise ExplanationContractError("output must be an ExplanationGeneratorOutput")
    if output.contract_version != SUPPORTED_CONTRACT_VERSION:
        raise ExplanationContractError("unsupported output contract_version")

    section_ids = [item.section_id for item in output.sections]
    substitution_ids = [item.substitution_id for item in output.terminology_substitutions]
    check_ids = [item.check_id for item in output.fidelity_checks]
    for values, label in (
        (section_ids, "section IDs"),
        (substitution_ids, "terminology substitution IDs"),
        (check_ids, "fidelity check IDs"),
    ):
        if len(values) != len(set(values)):
            raise ExplanationContractError(f"{label} must be unique")

    known_sections = set(section_ids)
    for check in output.fidelity_checks:
        if not set(check.section_ids) <= known_sections:
            raise ExplanationContractError("fidelity check references unknown section")

    trace_sequences = [event.sequence for event in output.explanation_trace]
    if trace_sequences != sorted(trace_sequences) or len(trace_sequences) != len(set(trace_sequences)):
        raise ExplanationContractError("explanation trace sequence values must be unique and ordered")
    for event in output.explanation_trace:
        if event.section_id is not None and event.section_id not in known_sections:
            raise ExplanationContractError("trace references unknown section")

    failed_checks = [item for item in output.fidelity_checks if item.status == "FAILED"]
    review_checks = [item for item in output.fidelity_checks if item.status == "REQUIRES_REVIEW"]
    if output.fidelity_status == "VERIFIED" and (failed_checks or review_checks):
        raise ExplanationContractError("verified fidelity cannot contain failed or review checks")
    if output.fidelity_status == "FAILED" and not failed_checks:
        raise ExplanationContractError("failed fidelity requires at least one failed check")
    if output.fidelity_status == "REQUIRES_REVIEW" and not review_checks:
        raise ExplanationContractError("review fidelity requires at least one review check")

    drafted_sections = [item for item in output.sections if item.status == "DRAFTED"]
    if output.explanation_status in {"DRAFTED", "DRAFTED_WITH_LIMITATIONS", "CLARIFICATION_DRAFTED"}:
        if not drafted_sections:
            raise ExplanationContractError("drafted explanation statuses require at least one drafted section")
        if output.fidelity_status == "FAILED":
            raise ExplanationContractError("failed fidelity cannot produce a drafted explanation")
    if output.explanation_status == "DRAFTED_WITH_LIMITATIONS" and not output.limitations:
        raise ExplanationContractError("drafted-with-limitations status requires limitations")
    if output.explanation_status == "CLARIFICATION_DRAFTED":
        if output.explanation_mode != "CLARIFICATION_REQUEST":
            raise ExplanationContractError("clarification draft requires clarification-request mode")
        if not any(item.section_type == "CLARIFICATION" for item in drafted_sections):
            raise ExplanationContractError("clarification draft requires a clarification section")

    if any(not item.meaning_preserved for item in output.terminology_substitutions):
        if output.fidelity_status not in {"FAILED", "REQUIRES_REVIEW"}:
            raise ExplanationContractError("meaning-changing terminology cannot be fidelity verified")

    return output
