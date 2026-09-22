"""Admission policy for governed customer-education publication."""
from __future__ import annotations

from dataclasses import dataclass

from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EDUCATION_PUBLICATION_STATUS,
    EDUCATION_REQUEST_USES,
    EducationPublicationRecord,
)


class EducationPublicationAdmissionError(ValueError):
    """Raised when an education-admission request is structurally invalid."""


@dataclass(frozen=True)
class EducationAdmissionDecision:
    requested_use: str
    admitted: bool
    basis: str
    publication_id: str | None
    publication_receipt_id: str | None


def evaluate_education_admission(
    *,
    publication: EducationPublicationRecord | None,
    requested_use: str,
    concept_id: str | None = None,
) -> EducationAdmissionDecision:
    """Admit a published education asset only for its explicitly authorized use."""
    if requested_use not in EDUCATION_REQUEST_USES:
        raise EducationPublicationAdmissionError(
            f"requested_use must be one of {sorted(EDUCATION_REQUEST_USES)}"
        )
    if publication is None:
        return EducationAdmissionDecision(
            requested_use=requested_use,
            admitted=False,
            basis="customer education requires an explicit education publication receipt",
            publication_id=None,
            publication_receipt_id=None,
        )
    if not isinstance(publication, EducationPublicationRecord):
        raise EducationPublicationAdmissionError(
            "publication must be an EducationPublicationRecord or None"
        )
    if publication.publication_status != EDUCATION_PUBLICATION_STATUS:
        return EducationAdmissionDecision(
            requested_use=requested_use,
            admitted=False,
            basis="education publication status is not authoritative",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if not publication.publication_receipt_id.strip():
        return EducationAdmissionDecision(
            requested_use=requested_use,
            admitted=False,
            basis="education publication receipt is missing",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if concept_id is not None:
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise EducationPublicationAdmissionError(
                "concept_id must be a non-empty string when provided"
            )
        if publication.concept_id != concept_id.strip():
            return EducationAdmissionDecision(
                requested_use=requested_use,
                admitted=False,
                basis="education publication concept does not match requested concept",
                publication_id=publication.publication_id,
                publication_receipt_id=publication.publication_receipt_id,
            )
    if requested_use not in publication.allowed_uses:
        return EducationAdmissionDecision(
            requested_use=requested_use,
            admitted=False,
            basis="education publication does not authorize the requested use",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if requested_use != CUSTOMER_EDUCATION:
        return EducationAdmissionDecision(
            requested_use=requested_use,
            admitted=False,
            basis="education publication cannot authorize operative product facts",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    return EducationAdmissionDecision(
        requested_use=requested_use,
        admitted=True,
        basis="reviewed education publication admits customer-education use only",
        publication_id=publication.publication_id,
        publication_receipt_id=publication.publication_receipt_id,
    )


__all__ = [
    "EducationAdmissionDecision",
    "EducationPublicationAdmissionError",
    "evaluate_education_admission",
]
