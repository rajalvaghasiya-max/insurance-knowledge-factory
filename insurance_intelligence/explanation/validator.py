"""Deterministic fidelity and safety validation for explanation drafts (MO-019D)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Mapping, Sequence

from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorInput,
    ExplanationSection,
    FidelityCheck,
    TerminologySubstitution,
    build_fidelity_check,
)
from insurance_intelligence.contracts.reasoning import Finding


class ExplanationValidationError(ValueError):
    """Raised when explanation fidelity validation cannot be performed safely."""


VALIDATION_STATUSES = frozenset(
    {
        "VERIFIED",
        "VERIFIED_WITH_LIMITATIONS",
        "FAILED_MISSING_CONDITION",
        "FAILED_NUMERIC_CHANGE",
        "FAILED_MISSING_LIMITATION",
        "FAILED_UNSUPPORTED_CONTENT",
        "FAILED_EVIDENCE_REFERENCE",
        "FAILED_DECISION_SCOPE",
        "FAILED_CLARIFICATION_FIDELITY",
        "REQUIRES_REVIEW",
    }
)

_RECOMMENDATION_PATTERNS = (
    re.compile(r"\b(should|must)\s+(buy|choose|purchase|switch|avoid|recommend)\b", re.I),
    re.compile(r"\b(best|better|suitable|unsuitable)\s+(plan|policy|product|for you)\b", re.I),
    re.compile(r"\bwe recommend\b", re.I),
)
_CURRENCY_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s*\d[\d,]*(?:\.\d+)?", re.I)
_NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
_MALFORMED_CONDITION_PATTERN = re.compile(r"\bwhen\s+where\b", re.I)
_POSITIVE_OBLIGATION_PATTERN = re.compile(r"\b(must bear|must pay|you pay|co-payment applies|obligation applies)\b", re.I)


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalise(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _numbers(value: str) -> tuple[str, ...]:
    return tuple(_NUMBER_PATTERN.findall(value))


def _section_text(sections: Sequence[ExplanationSection]) -> str:
    return " ".join(section.text for section in sections if section.status == "DRAFTED")


def _finding_sections(
    sections: Sequence[ExplanationSection], finding_id: str
) -> tuple[ExplanationSection, ...]:
    return tuple(section for section in sections if finding_id in section.approved_finding_ids)


def _check(
    *,
    request_id: str,
    check_type: str,
    status: str,
    description: str,
    source_references: Sequence[str] = (),
    section_ids: Sequence[str] = (),
) -> FidelityCheck:
    return build_fidelity_check(
        check_id=_stable_id("fidelity", request_id, check_type, description),
        check_type=check_type,
        status=status,
        description=description,
        source_references=tuple(sorted(set(source_references))),
        section_ids=tuple(sorted(set(section_ids))),
    )


@dataclass(frozen=True)
class FidelityValidationResult:
    validation_status: str
    fidelity_status: str
    checks: tuple[FidelityCheck, ...]
    limitations: tuple[str, ...]
    confidence: float


def validate_explanation_fidelity(
    *,
    explanation_input: ExplanationGeneratorInput,
    sections: Sequence[ExplanationSection],
    findings_by_id: Mapping[str, Finding],
    terminology_substitutions: Sequence[TerminologySubstitution] = (),
) -> FidelityValidationResult:
    if not isinstance(explanation_input, ExplanationGeneratorInput):
        raise ExplanationValidationError("explanation_input must be validated")
    if any(not isinstance(section, ExplanationSection) for section in sections):
        raise ExplanationValidationError("sections must contain ExplanationSection values")
    if any(not isinstance(item, TerminologySubstitution) for item in terminology_substitutions):
        raise ExplanationValidationError("terminology_substitutions must contain validated values")

    decision = explanation_input.decision_output
    drafted = tuple(section for section in sections if section.status == "DRAFTED")
    all_text = _section_text(drafted)
    checks: list[FidelityCheck] = []
    failures: list[str] = []
    limitations: list[str] = []

    if decision.decision == "CLARIFICATION_REQUIRED":
        expected_ids = tuple(sorted(item.clarification_id for item in decision.clarifications))
        actual_ids = tuple(sorted({item for section in drafted for item in section.clarification_ids}))
        ordinary = tuple(section for section in drafted if section.section_type != "CLARIFICATION")
        if ordinary or actual_ids != expected_ids:
            failures.append("FAILED_CLARIFICATION_FIDELITY")
            checks.append(
                _check(
                    request_id=explanation_input.request_id,
                    check_type="APPROVED_FINDING_COVERAGE",
                    status="FAILED",
                    description="Clarification draft must contain only the approved clarification requirements.",
                    source_references=expected_ids,
                    section_ids=tuple(item.section_id for item in drafted),
                )
            )
        else:
            checks.append(
                _check(
                    request_id=explanation_input.request_id,
                    check_type="APPROVED_FINDING_COVERAGE",
                    status="PASSED",
                    description="All approved clarification requirements are preserved without ordinary findings.",
                    source_references=expected_ids,
                    section_ids=tuple(item.section_id for item in drafted),
                )
            )
        unsupported = any(pattern.search(all_text) for pattern in _RECOMMENDATION_PATTERNS)
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="NO_RECOMMENDATION",
                status="FAILED" if unsupported else "PASSED",
                description="Clarification wording does not introduce recommendation language." if not unsupported else "Clarification wording introduces recommendation language.",
                section_ids=tuple(item.section_id for item in drafted),
            )
        )
        if unsupported:
            failures.append("FAILED_UNSUPPORTED_CONTENT")
        return _result(checks, failures, limitations)

    packet = decision.response_packet
    if packet is None:
        raise ExplanationValidationError("approved decision requires an approved response packet")

    approved_ids = tuple(sorted(packet.approved_finding_ids))
    unknown = tuple(item for item in approved_ids if item not in findings_by_id)
    if unknown:
        raise ExplanationValidationError(f"approved findings are missing from findings_by_id: {unknown}")

    section_finding_ids = {item for section in drafted for item in section.approved_finding_ids}
    coverage_ok = set(approved_ids) <= section_finding_ids
    checks.append(
        _check(
            request_id=explanation_input.request_id,
            check_type="APPROVED_FINDING_COVERAGE",
            status="PASSED" if coverage_ok else "FAILED",
            description="All approved findings are represented." if coverage_ok else "One or more approved findings are missing.",
            source_references=approved_ids,
            section_ids=tuple(item.section_id for item in drafted),
        )
    )
    if not coverage_ok:
        failures.append("FAILED_DECISION_SCOPE")

    withheld_ids = {
        item.finding_id
        for item in decision.finding_dispositions
        if item.disposition not in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}
    }
    leaked = withheld_ids.intersection(section_finding_ids)
    checks.append(
        _check(
            request_id=explanation_input.request_id,
            check_type="NO_WITHHELD_CONTENT",
            status="FAILED" if leaked else "PASSED",
            description="No withheld finding content is exposed." if not leaked else "Withheld finding content is exposed.",
            source_references=tuple(sorted(leaked)),
            section_ids=tuple(item.section_id for item in drafted),
        )
    )
    if leaked:
        failures.append("FAILED_DECISION_SCOPE")

    for finding_id in approved_ids:
        finding = findings_by_id[finding_id]
        related = _finding_sections(drafted, finding_id)
        related_text = _section_text(related)
        related_ids = tuple(item.section_id for item in related)
        evidence_seen = {item for section in related for item in section.evidence_ids}
        evidence_ok = set(finding.evidence_ids) <= evidence_seen
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="EVIDENCE_REFERENCE_PRESERVATION",
                status="PASSED" if evidence_ok else "FAILED",
                description=f"Evidence references are preserved for {finding_id}." if evidence_ok else f"Evidence references are missing for {finding_id}.",
                source_references=finding.evidence_ids,
                section_ids=related_ids,
            )
        )
        if not evidence_ok:
            failures.append("FAILED_EVIDENCE_REFERENCE")

        condition_ok = not finding.condition or _normalise(finding.condition) in _normalise(related_text)
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="CONDITION_PRESERVATION",
                status="PASSED" if condition_ok else "FAILED",
                description=f"Material condition is preserved for {finding_id}." if condition_ok else f"Material condition is missing for {finding_id}.",
                source_references=(finding_id,),
                section_ids=related_ids,
            )
        )
        if not condition_ok:
            failures.append("FAILED_MISSING_CONDITION")

        semantic_values = tuple(filter(None, (finding.trigger or finding.condition, finding.exception, finding.applicability_scope)))
        malformed = bool(_MALFORMED_CONDITION_PATTERN.search(related_text))
        conflated = bool(
            finding.trigger
            and finding.exception
            and (
                _normalise(finding.exception) in _normalise(finding.trigger)
                or "not apply" in _normalise(finding.trigger)
            )
        )
        exception_ok = not finding.exception or _normalise(finding.exception) in _normalise(related_text)
        scope_ok = not finding.applicability_scope or _normalise(finding.applicability_scope) in _normalise(related_text)
        unresolved_obligation = finding.predicate == "requires_trigger_context" and bool(_POSITIVE_OBLIGATION_PATTERN.search(related_text))
        nonapp_obligation = finding.predicate == "is_not_triggered" and bool(_POSITIVE_OBLIGATION_PATTERN.search(related_text))
        semantic_ok = not any((malformed, conflated, not exception_ok, not scope_ok, unresolved_obligation, nonapp_obligation))
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="CONDITIONAL_SEMANTIC_INTEGRITY",
                status="PASSED" if semantic_ok else "FAILED",
                description=(
                    f"Trigger, exception, scope and applicability outcome are preserved for {finding_id}."
                    if semantic_ok
                    else f"Conditional semantics are unsafe or incomplete for {finding_id}."
                ),
                source_references=(finding_id,),
                section_ids=related_ids,
            )
        )
        if not semantic_ok:
            failures.append("FAILED_MISSING_CONDITION" if (not exception_ok or not scope_ok) else "FAILED_UNSUPPORTED_CONTENT")

        source_numbers = set(_numbers(" ".join(filter(None, (finding.object_or_effect,) + semantic_values))))
        rendered_numbers = set(_numbers(related_text))
        numeric_ok = source_numbers <= rendered_numbers and not (rendered_numbers - source_numbers)
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="NO_NEW_FACTS",
                status="PASSED" if numeric_ok else "FAILED",
                description=f"Numeric terms are preserved for {finding_id}." if numeric_ok else f"Numeric terms changed or were introduced for {finding_id}.",
                source_references=(finding_id,),
                section_ids=related_ids,
            )
        )
        if not numeric_ok:
            failures.append("FAILED_NUMERIC_CHANGE")

        limitation_seen = {item for section in drafted for item in section.limitation_ids}
        finding_limitations = set(finding.limitations).intersection(packet.limitation_ids)
        limitation_ok = finding_limitations <= limitation_seen
        checks.append(
            _check(
                request_id=explanation_input.request_id,
                check_type="LIMITATION_PRESERVATION",
                status="PASSED" if limitation_ok else "FAILED",
                description=f"Limitations are preserved for {finding_id}." if limitation_ok else f"Limitations are missing for {finding_id}.",
                source_references=tuple(sorted(finding_limitations)),
                section_ids=tuple(item.section_id for item in drafted if item.limitation_ids),
            )
        )
        if not limitation_ok:
            failures.append("FAILED_MISSING_LIMITATION")

    meaning_change = tuple(item for item in terminology_substitutions if not item.meaning_preserved)
    checks.append(
        _check(
            request_id=explanation_input.request_id,
            check_type="TERMINOLOGY_ACCURACY",
            status="FAILED" if meaning_change else "PASSED",
            description="Terminology substitutions preserve meaning." if not meaning_change else "One or more terminology substitutions change meaning.",
            source_references=tuple(item.substitution_id for item in meaning_change),
            section_ids=tuple(item.section_id for item in drafted),
        )
    )
    if meaning_change:
        failures.append("FAILED_UNSUPPORTED_CONTENT")

    unsupported = any(pattern.search(all_text) for pattern in _RECOMMENDATION_PATTERNS)
    new_currency = bool(_CURRENCY_PATTERN.search(all_text)) and not any(
        _CURRENCY_PATTERN.search(" ".join(filter(None, (findings_by_id[item].object_or_effect, findings_by_id[item].condition, findings_by_id[item].exception, findings_by_id[item].applicability_scope))))
        for item in approved_ids
    )
    checks.append(
        _check(
            request_id=explanation_input.request_id,
            check_type="NO_RECOMMENDATION",
            status="FAILED" if unsupported else "PASSED",
            description="No recommendation or suitability language is introduced." if not unsupported else "Recommendation or suitability language is introduced.",
            section_ids=tuple(item.section_id for item in drafted),
        )
    )
    checks.append(
        _check(
            request_id=explanation_input.request_id,
            check_type="NO_NEW_REASONING",
            status="FAILED" if new_currency else "PASSED",
            description="No unsupported financial calculation is introduced." if not new_currency else "An unsupported financial amount is introduced.",
            section_ids=tuple(item.section_id for item in drafted),
        )
    )
    if unsupported or new_currency:
        failures.append("FAILED_UNSUPPORTED_CONTENT")

    if decision.decision == "APPROVED_WITH_LIMITATIONS" and packet.limitation_ids:
        limitations.extend(decision.limitations)

    return _result(checks, failures, limitations)


def _result(
    checks: Sequence[FidelityCheck], failures: Sequence[str], limitations: Sequence[str]
) -> FidelityValidationResult:
    ordered_checks = tuple(sorted(checks, key=lambda item: (item.check_type, item.check_id)))
    unique_failures = tuple(dict.fromkeys(failures))
    unique_limitations = tuple(dict.fromkeys(item for item in limitations if item))
    failure_priority = (
        "FAILED_CLARIFICATION_FIDELITY",
        "FAILED_DECISION_SCOPE",
        "FAILED_UNSUPPORTED_CONTENT",
        "FAILED_EVIDENCE_REFERENCE",
        "FAILED_MISSING_CONDITION",
        "FAILED_NUMERIC_CHANGE",
        "FAILED_MISSING_LIMITATION",
    )
    if unique_failures:
        status = next(item for item in failure_priority if item in unique_failures)
        fidelity_status = "FAILED"
        confidence = 0.0
    elif unique_limitations:
        status = "VERIFIED_WITH_LIMITATIONS"
        fidelity_status = "VERIFIED_WITH_LIMITATIONS"
        confidence = 0.9
    else:
        status = "VERIFIED"
        fidelity_status = "VERIFIED"
        confidence = 1.0
    if status not in VALIDATION_STATUSES:
        raise ExplanationValidationError(f"unsupported validation status: {status}")
    return FidelityValidationResult(
        validation_status=status,
        fidelity_status=fidelity_status,
        checks=ordered_checks,
        limitations=unique_limitations,
        confidence=confidence,
    )
