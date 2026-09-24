"""Deterministic rendering and admission for governed education publications."""
from __future__ import annotations

from typing import Mapping, Sequence

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EducationPublicationRecord,
)
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorInput,
    ExplanationSection,
    PracticalIllustrationProfile,
    build_section,
)
from insurance_intelligence.education_publication.admission import (
    evaluate_education_admission,
)
from insurance_intelligence.contracts.reasoning import Finding


class EducationExplanationError(ValueError):
    """Raised when education content cannot enter an explanation safely."""


def _sentence(value: str) -> str:
    text = " ".join(value.strip().split())
    if not text:
        raise EducationExplanationError("education text must not be empty")
    return text if text[-1] in ".?!" else text + "."


def _education_text(publication: EducationPublicationRecord) -> str:
    """Render reviewed customer education without leading with source-legal wording.

    The formal definition remains preserved in the immutable publication for audit
    and governance. Customer education uses the separately reviewed plain-language
    explanation and practical implication fields only.
    """
    return " ".join(
        (
            _sentence(
                f"{publication.canonical_name}: "
                f"{publication.plain_language_explanation}"
            ),
            _sentence(publication.practical_implication),
        )
    )


def _example_text(*, scenario: str, result: str, boundary: str) -> str:
    return " ".join(
        (
            _sentence(f"Example: {scenario}"),
            _sentence(result),
            _sentence(boundary),
        )
    )


def admitted_publications(
    explanation_input: ExplanationGeneratorInput,
) -> tuple[EducationPublicationRecord, ...]:
    publications = tuple(explanation_input.education_publications)
    if not publications:
        return ()
    if explanation_input.audience != "CUSTOMER":
        raise EducationExplanationError(
            "customer education publication is eligible for CUSTOMER audience only"
        )
    if explanation_input.decision_output.decision == "CLARIFICATION_REQUIRED":
        raise EducationExplanationError(
            "education enrichment is not authorized on clarification responses"
        )

    admitted: list[EducationPublicationRecord] = []
    for publication in publications:
        decision = evaluate_education_admission(
            publication=publication,
            requested_use=CUSTOMER_EDUCATION,
            concept_id=publication.concept_id,
        )
        if not decision.admitted:
            raise EducationExplanationError(
                f"education publication {publication.publication_id!r} was not admitted: "
                f"{decision.basis}"
            )
        admitted.append(publication)
    return tuple(sorted(admitted, key=lambda item: item.publication_id))


def render_education_sections(
    *,
    request_id: str,
    publications: Sequence[EducationPublicationRecord],
) -> tuple[ExplanationSection, ...]:
    sections: list[ExplanationSection] = []
    for publication in publications:
        sections.append(
            build_section(
                section_id=f"education:{request_id}:{publication.publication_id}:meaning",
                section_type="EDUCATION",
                status="DRAFTED",
                text=_education_text(publication),
                education_publication_ids=(publication.publication_id,),
            )
        )
        for index, example in enumerate(publication.examples, start=1):
            sections.append(
                build_section(
                    section_id=(
                        f"education:{request_id}:{publication.publication_id}:"
                        f"example:{index:03d}"
                    ),
                    section_type="EXAMPLE",
                    status="DRAFTED",
                    text=_example_text(
                        scenario=example.scenario,
                        result=example.result,
                        boundary=example.boundary,
                    ),
                    education_publication_ids=(publication.publication_id,),
                )
            )
    return tuple(sections)



def _semantic_attribute_map(finding: Finding) -> dict[str, str]:
    return {item.key: item.value for item in finding.semantic_attributes}


def _duration_candidate(
    *,
    approved_finding_ids: Sequence[str],
    findings_by_id: Mapping[str, Finding],
    duration_unit: str,
) -> tuple[Finding, int] | None:
    candidates: list[tuple[Finding, int, str | None]] = []
    for finding_id in approved_finding_ids:
        finding = findings_by_id.get(finding_id)
        if finding is None:
            continue
        attributes = _semantic_attribute_map(finding)
        raw_value = attributes.get("duration_value")
        raw_unit = attributes.get("duration_unit")
        if raw_value is None or raw_unit is None:
            continue
        if raw_unit.upper() != duration_unit.upper():
            continue
        try:
            numeric = int(raw_value)
        except (TypeError, ValueError):
            continue
        if numeric < 1 or str(numeric) != str(raw_value).strip():
            continue
        candidates.append((finding, numeric, attributes.get("answer_role")))

    primary = tuple(item for item in candidates if item[2] == "PRIMARY")
    selected = primary if primary else tuple(candidates)
    if len(selected) != 1:
        return None
    finding, value, _ = selected[0]
    return finding, value


def _render_profile_text(
    *,
    profile: PracticalIllustrationProfile,
    duration_value: int,
) -> str:
    values = {
        "related_condition": profile.related_condition,
        "unrelated_condition": profile.unrelated_condition,
        "before_probe_value": profile.before_probe_value,
        "after_probe_value": profile.after_probe_value,
        "duration_value": duration_value,
        "duration_unit": profile.duration_unit,
        "duration_unit_lower": profile.duration_unit.lower(),
    }
    parts = (
        profile.during_wait_template.format_map(values),
        profile.unrelated_condition_template.format_map(values),
        profile.after_wait_template.format_map(values),
        profile.boundary_text.format_map(values),
    )
    return " ".join(_sentence(item) for item in parts)


def render_practical_illustration_sections(
    *,
    request_id: str,
    profiles: Sequence[PracticalIllustrationProfile],
    publications: Sequence[EducationPublicationRecord],
    approved_finding_ids: Sequence[str],
    findings_by_id: Mapping[str, Finding],
) -> tuple[ExplanationSection, ...]:
    if not profiles or not publications:
        return ()

    publication_by_concept: dict[str, EducationPublicationRecord] = {}
    duplicate_concepts: set[str] = set()
    for publication in publications:
        if publication.concept_id in publication_by_concept:
            duplicate_concepts.add(publication.concept_id)
        else:
            publication_by_concept[publication.concept_id] = publication

    sections: list[ExplanationSection] = []
    for profile in profiles:
        if profile.concept_id in duplicate_concepts:
            continue
        publication = publication_by_concept.get(profile.concept_id)
        if publication is None:
            continue
        candidate = _duration_candidate(
            approved_finding_ids=approved_finding_ids,
            findings_by_id=findings_by_id,
            duration_unit=profile.duration_unit,
        )
        if candidate is None:
            continue
        finding, duration_value = candidate
        if not (
            profile.before_probe_value < duration_value < profile.after_probe_value
        ):
            continue
        sections.append(
            build_section(
                section_id=(
                    f"illustration:{request_id}:{profile.profile_id}:"
                    f"{finding.finding_id}"
                ),
                section_type="PRACTICAL_ILLUSTRATION",
                status="DRAFTED",
                text=_render_profile_text(
                    profile=profile,
                    duration_value=duration_value,
                ),
                approved_finding_ids=(finding.finding_id,),
                evidence_ids=finding.evidence_ids,
                education_publication_ids=(publication.publication_id,),
            )
        )
    return tuple(sections)


__all__ = [
    "EducationExplanationError",
    "admitted_publications",
    "render_education_sections",
    "render_practical_illustration_sections",
]
