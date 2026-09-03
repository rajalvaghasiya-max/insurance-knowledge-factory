"""Publication-aware admission policy for runtime evidence use.

Internal certification is intentionally distinct from ordinary user-answer evidence use.
The policy is pure and does not retrieve, publish, or mutate knowledge. It only decides
whether an already-created authoritative publication record is sufficient admission
proof for downstream answer evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    PUBLICATION_STATUS,
)

EVIDENCE_USE_KEY = "evidence_use"
INTERNAL_CERTIFICATION = "INTERNAL_CERTIFICATION"
USER_ANSWER = "USER_ANSWER"
EVIDENCE_USES = frozenset({INTERNAL_CERTIFICATION, USER_ANSWER})


class EvidenceAdmissionError(ValueError):
    """Raised when evidence-use or publication-admission inputs are invalid."""


@dataclass(frozen=True)
class PublicationAdmissionDecision:
    evidence_use: str
    admitted: bool
    basis: str
    publication_id: str | None
    publication_receipt_id: str | None


def evidence_use_from_context(context: Mapping[str, object]) -> str:
    """Resolve the governed evidence-use mode from resolver context.

    Historical MO-016 callers predate publication-aware answer admission, so absence of
    the key preserves their internal-certification behavior. New ordinary answer paths
    must set ``evidence_use=USER_ANSWER`` explicitly.
    """
    if not isinstance(context, Mapping):
        raise EvidenceAdmissionError("resolution context must be a mapping")
    value = context.get(EVIDENCE_USE_KEY, INTERNAL_CERTIFICATION)
    if not isinstance(value, str) or value not in EVIDENCE_USES:
        raise EvidenceAdmissionError(
            f"{EVIDENCE_USE_KEY} must be one of {sorted(EVIDENCE_USES)}"
        )
    return value


def evaluate_publication_admission(
    *,
    evidence_use: str,
    publication: AuthoritativePublicationRecord | None,
    governed_subject_reference: str | None = None,
    topic_id: str | None = None,
) -> PublicationAdmissionDecision:
    """Decide whether evidence may enter the requested downstream use.

    INTERNAL_CERTIFICATION intentionally does not require authoritative publication;
    certification/evaluation must remain able to test governed-but-unpublished bindings.
    USER_ANSWER requires an exact authoritative publication record and fails closed on
    missing/mismatched identity, topic, receipt, status, or preserved publication boundary.
    """
    if evidence_use not in EVIDENCE_USES:
        raise EvidenceAdmissionError(
            f"evidence_use must be one of {sorted(EVIDENCE_USES)}"
        )
    if evidence_use == INTERNAL_CERTIFICATION:
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=True,
            basis="internal certification use does not require authoritative publication",
            publication_id=None,
            publication_receipt_id=None,
        )

    if publication is None:
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis="ordinary user-answer evidence requires authoritative publication",
            publication_id=None,
            publication_receipt_id=None,
        )
    if not isinstance(publication, AuthoritativePublicationRecord):
        raise EvidenceAdmissionError(
            "publication must be an AuthoritativePublicationRecord or None"
        )
    if publication.publication_status != PUBLICATION_STATUS:
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis=f"publication status is {publication.publication_status!r}, not {PUBLICATION_STATUS!r}",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if not publication.publication_receipt_id.strip():
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis="authoritative publication receipt is missing",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if governed_subject_reference is not None and (
        publication.governed_subject_reference != governed_subject_reference
    ):
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis="authoritative publication governed subject does not match resolved evidence subject",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if topic_id is not None and publication.topic_id != topic_id:
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis="authoritative publication topic does not match resolved evidence topic",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    if any("bound_not_published" in item.casefold() for item in publication.limitations):
        return PublicationAdmissionDecision(
            evidence_use=evidence_use,
            admitted=False,
            basis="bound_not_published cannot be admitted to ordinary user-answer evidence",
            publication_id=publication.publication_id,
            publication_receipt_id=publication.publication_receipt_id,
        )
    return PublicationAdmissionDecision(
        evidence_use=evidence_use,
        admitted=True,
        basis="authoritative publication record admits ordinary user-answer evidence",
        publication_id=publication.publication_id,
        publication_receipt_id=publication.publication_receipt_id,
    )


__all__ = [
    "EVIDENCE_USE_KEY",
    "EVIDENCE_USES",
    "EvidenceAdmissionError",
    "INTERNAL_CERTIFICATION",
    "PublicationAdmissionDecision",
    "USER_ANSWER",
    "evaluate_publication_admission",
    "evidence_use_from_context",
]
