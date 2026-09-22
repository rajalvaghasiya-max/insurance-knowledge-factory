"""Deterministic rendering and admission for governed education publications."""
from __future__ import annotations

from typing import Sequence

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EducationPublicationRecord,
)
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorInput,
    ExplanationSection,
    build_section,
)
from insurance_intelligence.education_publication.admission import (
    evaluate_education_admission,
)


class EducationExplanationError(ValueError):
    """Raised when education content cannot enter an explanation safely."""


def _sentence(value: str) -> str:
    text = " ".join(value.strip().split())
    if not text:
        raise EducationExplanationError("education text must not be empty")
    return text if text[-1] in ".?!" else text + "."


def _education_text(publication: EducationPublicationRecord) -> str:
    return " ".join(
        (
            _sentence(f"{publication.canonical_name}: {publication.definition}"),
            _sentence(publication.plain_language_explanation),
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


__all__ = [
    "EducationExplanationError",
    "admitted_publications",
    "render_education_sections",
]
