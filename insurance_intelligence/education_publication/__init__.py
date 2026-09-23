"""Governed customer-education publication and admission."""

from insurance_intelligence.education_publication.admission import (
    EducationAdmissionDecision,
    EducationPublicationAdmissionError,
    evaluate_education_admission,
)
from insurance_intelligence.education_publication.gate import (
    EducationPublicationGateError,
    create_education_publication,
)
from insurance_intelligence.education_publication.repository import (
    EducationPublicationRepository,
    EducationPublicationRepositoryError,
    GovernedEducationPublicationLookup,
)

__all__ = [
    "EducationAdmissionDecision",
    "EducationPublicationAdmissionError",
    "EducationPublicationGateError",
    "EducationPublicationRepository",
    "EducationPublicationRepositoryError",
    "GovernedEducationPublicationLookup",
    "create_education_publication",
    "evaluate_education_admission",
]
