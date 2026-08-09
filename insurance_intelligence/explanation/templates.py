"""Deterministic explanation templates for evidence-locked approved findings (MO-019C)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence

from insurance_intelligence.contracts.decision import DecisionGateOutput
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorInput,
    ExplanationSection,
    TerminologySubstitution,
    build_section,
    build_terminology_substitution,
)
from insurance_intelligence.contracts.reasoning import Finding
from insurance_intelligence.explanation.registry import (
    ExplanationStyleDefinition,
    TerminologyDefinition,
)


class ExplanationTemplateError(ValueError):
    """Raised when deterministic explanation rendering cannot proceed safely."""


_NON_RENDERABLE_FINDING_STATUSES = frozenset({"CONFLICTING", "UNSUPPORTED", "BLOCKED"})


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def _normalise_space(value: str) -> str:
    return " ".join(value.strip().split())


def _ensure_sentence(value: str) -> str:
    text = _normalise_space(value)
    if not text:
        raise ExplanationTemplateError("rendered text must not be empty")
    if text[-1] not in ".?!":
        text += "."
    return text


def _join_subject_predicate(finding: Finding) -> str:
    subject = _normalise_space(finding.subject)
    predicate = _normalise_space(finding.predicate).replace("_", " ")
    effect = _normalise_space(finding.object_or_effect)
    return _ensure_sentence(f"{subject} {predicate} {effect}")


def _customer_subject(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"insured", "policyholder", "customer", "you"}:
        return "you"
    return value.strip()


def _semantic_clauses(finding: Finding) -> tuple[str | None, str | None, str | None]:
    return (
        finding.trigger or finding.condition,
        finding.exception,
        finding.applicability_scope,
    )


def _validate_renderable_status(finding: Finding) -> None:
    if finding.finding_status in _NON_RENDERABLE_FINDING_STATUSES:
        raise ExplanationTemplateError(
            "approved finding status is not eligible for explanation rendering: "
            + finding.finding_status
        )


def _apply_status_language(finding: Finding, text: str) -> str:
    """Make uncertainty/limitations explicit without altering supported semantics."""
    if finding.finding_status == "PARTIALLY_SUPPORTED":
        return _ensure_sentence(
            "This finding is only partially supported by the approved evidence. " + text
        )
    if finding.finding_status == "SUPPORTED_WITH_LIMITATIONS":
        return _ensure_sentence(
            "This finding is supported with limitations. " + text
        )
    return text


def _plain_finding_text(finding: Finding, *, audience: str) -> str:
    subject = _customer_subject(finding.subject) if audience == "CUSTOMER" else finding.subject.strip()
    predicate = finding.predicate.strip().replace("_", " ")
    effect = finding.object_or_effect.strip()
    trigger, exception, applicability_scope = _semantic_clauses(finding)
    clauses: list[str] = []
    if finding.predicate == "must_bear":
        clauses.append(_ensure_sentence(f"Trigger: {trigger}"))
        clauses.append(_ensure_sentence(f"Obligation: {subject} {predicate} {effect}"))
    elif finding.predicate == "is_not_triggered":
        clauses.append(_ensure_sentence(f"Trigger: {trigger}"))
        clauses.append(_ensure_sentence(f"Outcome: {effect}"))
    elif finding.predicate == "requires_trigger_context":
        clauses.append(_ensure_sentence(f"Trigger to confirm: {trigger}"))
        clauses.append(_ensure_sentence(f"Applicability: {effect}"))
    else:
        statement = f"{subject} {predicate} {effect}"
        clauses.append(_ensure_sentence(statement))
    if exception:
        clauses.append(_ensure_sentence(f"Exception: {exception}"))
    if applicability_scope:
        clauses.append(_ensure_sentence(f"Scope: {applicability_scope}"))
    return " ".join(clauses)


def _talking_point_text(finding: Finding) -> str:
    core = _plain_finding_text(finding, audience="ADVISOR")
    return _ensure_sentence(f"Explain that {core[0].lower() + core[1:].rstrip('.')}")


def _apply_term(text: str, item: TerminologyDefinition) -> tuple[str, bool]:
    if item.source_term not in text:
        return text, False
    rendered = item.rendered_term
    if item.action == "DEFINE":
        rendered = f"{item.rendered_term} ({item.definition_text})"
    elif item.action == "EXPAND":
        rendered = f"{item.rendered_term} — {item.definition_text}"
    return text.replace(item.source_term, rendered), True


@dataclass(frozen=True)
class TemplateRenderResult:
    sections: tuple[ExplanationSection, ...]
    terminology_substitutions: tuple[TerminologySubstitution, ...]
    template_ids: tuple[str, ...]


def render_explanation_templates(
    *,
    explanation_input: ExplanationGeneratorInput,
    findings_by_id: Mapping[str, Finding],
    style: ExplanationStyleDefinition,
    terminology: Sequence[TerminologyDefinition] = (),
) -> TemplateRenderResult:
    if not isinstance(explanation_input, ExplanationGeneratorInput):
        raise ExplanationTemplateError("explanation_input must be validated")
    if not isinstance(style, ExplanationStyleDefinition):
        raise ExplanationTemplateError("style must be an ExplanationStyleDefinition")
    if style.audience != explanation_input.audience or style.reading_level != explanation_input.reading_level:
        raise ExplanationTemplateError("style does not match explanation audience and reading level")
    if explanation_input.explanation_mode not in style.explanation_modes:
        raise ExplanationTemplateError("style does not support explanation mode")

    decision: DecisionGateOutput = explanation_input.decision_output
    if decision.decision == "CLARIFICATION_REQUIRED":
        sections = []
        for clarification in sorted(decision.clarifications, key=lambda item: item.clarification_id):
            question = explanation_input.communication_context.get(clarification.question_key)
            text = str(question).strip() if isinstance(question, str) and question.strip() else clarification.reason
            sections.append(
                build_section(
                    section_id=_stable_id("section", explanation_input.request_id, clarification.clarification_id),
                    section_type="CLARIFICATION",
                    status="DRAFTED",
                    text=_ensure_sentence(text),
                    clarification_ids=(clarification.clarification_id,),
                )
            )
        if not sections:
            raise ExplanationTemplateError("clarification decision contains no clarification requirements")
        return TemplateRenderResult(tuple(sections), (), ("clarification_request_v1",))

    packet = decision.response_packet
    if packet is None:
        raise ExplanationTemplateError("approved decision requires an approved response packet")

    approved_ids = tuple(sorted(packet.approved_finding_ids))
    missing = tuple(item for item in approved_ids if item not in findings_by_id)
    if missing:
        raise ExplanationTemplateError(f"approved findings are missing from findings_by_id: {missing}")

    sections: list[ExplanationSection] = []
    substitutions: list[TerminologySubstitution] = []
    template_ids: list[str] = []
    limitation_ids = tuple(sorted(packet.limitation_ids))

    for finding_id in approved_ids:
        finding = findings_by_id[finding_id]
        if finding.finding_id != finding_id:
            raise ExplanationTemplateError("finding map key must match finding.finding_id")
        if not finding.evidence_ids:
            raise ExplanationTemplateError("approved findings must preserve evidence IDs")
        _validate_renderable_status(finding)

        if explanation_input.explanation_mode == "ADVISOR_TALKING_POINTS":
            section_type = "ADVISOR_TALKING_POINT"
            text = _talking_point_text(finding)
            template_id = "advisor_talking_point_v1"
        elif explanation_input.explanation_mode == "DETAILED":
            section_type = "MEANING"
            if finding.exception or finding.applicability_scope:
                text = _plain_finding_text(finding, audience=explanation_input.audience)
            else:
                text = _join_subject_predicate(finding)
                if finding.condition:
                    text = _ensure_sentence(f"This applies when {finding.condition.strip()}. {text}")
            template_id = "detailed_finding_v1"
        else:
            section_type = "MEANING"
            text = _plain_finding_text(finding, audience=explanation_input.audience)
            template_id = "plain_finding_v1"

        text = _apply_status_language(finding, text)

        for term in sorted(terminology, key=lambda item: (item.priority, item.terminology_id, item.terminology_version)):
            if term.audience != explanation_input.audience:
                continue
            if explanation_input.reading_level not in term.reading_levels:
                continue
            if explanation_input.explanation_mode not in term.explanation_modes:
                continue
            text, applied = _apply_term(text, term)
            if applied:
                substitutions.append(
                    build_terminology_substitution(
                        substitution_id=_stable_id("term", finding_id, term.terminology_id, term.terminology_version),
                        source_term=term.source_term,
                        rendered_term=term.rendered_term,
                        action=term.action,
                        approved_finding_ids=(finding_id,),
                        meaning_preserved=term.meaning_preserved,
                    )
                )

        section_limitations = tuple(sorted(set(finding.limitations).intersection(limitation_ids)))
        sections.append(
            build_section(
                section_id=_stable_id("section", explanation_input.request_id, finding_id, template_id),
                section_type=section_type,
                status="DRAFTED",
                text=text,
                approved_finding_ids=(finding_id,),
                evidence_ids=tuple(sorted(finding.evidence_ids)),
                limitation_ids=section_limitations,
            )
        )
        template_ids.append(template_id)

        if style.preserve_conditions:
            trigger, exception, applicability_scope = _semantic_clauses(finding)
            for clause_type, clause_text in (
                ("TRIGGER", trigger),
                ("EXCEPTION", exception),
                ("SCOPE", applicability_scope),
            ):
                if not clause_text:
                    continue
                sections.append(
                    build_section(
                        section_id=_stable_id("section", explanation_input.request_id, finding_id, clause_type.lower()),
                        section_type="CONDITION",
                        status="DRAFTED",
                        text=_ensure_sentence(f"{clause_type.title()}: {clause_text}"),
                        approved_finding_ids=(finding_id,),
                        evidence_ids=tuple(sorted(finding.evidence_ids)),
                    )
                )
                template_ids.append("condition_notice_v1" if clause_type == "TRIGGER" else f"{clause_type.lower()}_notice_v1")

    if limitation_ids and style.preserve_limitations:
        sections.append(
            build_section(
                section_id=_stable_id("section", explanation_input.request_id, "limitations"),
                section_type="LIMITATION",
                status="DRAFTED",
                text=_ensure_sentence("Important limitations remain and must be read with this explanation"),
                limitation_ids=limitation_ids,
            )
        )
        template_ids.append("limitation_notice_v1")

    if style.preserve_evidence_notes and packet.approved_evidence_ids:
        sections.append(
            build_section(
                section_id=_stable_id("section", explanation_input.request_id, "evidence-note"),
                section_type="EVIDENCE_NOTE",
                status="DRAFTED",
                text="This explanation is based only on the approved policy evidence.",
                evidence_ids=tuple(sorted(packet.approved_evidence_ids)),
            )
        )
        template_ids.append("evidence_note_v1")

    if any(len(section.text.split()) > style.max_section_words for section in sections):
        raise ExplanationTemplateError("rendered section exceeds style max_section_words")

    return TemplateRenderResult(
        sections=tuple(sections),
        terminology_substitutions=tuple(sorted(substitutions, key=lambda item: item.substitution_id)),
        template_ids=tuple(template_ids),
    )
