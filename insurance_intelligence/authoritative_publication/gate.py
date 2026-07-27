"""Deterministic authoritative-publication gate (P2.4)."""

from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationInput,
    AuthoritativePublicationRecord,
    PUBLICATION_STATUS,
)


class AuthoritativePublicationGateError(ValueError):
    """Raised when authoritative publication is not safely permitted."""


def _contains_boundary(values: tuple[str, ...], token: str) -> bool:
    normalized = token.casefold()
    return any(normalized in item.casefold() for item in values)


def _stable_receipt_id(*parts: str) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"publication_receipt_{digest}"


def create_authoritative_publication(
    publication_input: AuthoritativePublicationInput,
) -> AuthoritativePublicationRecord:
    """Create an immutable authoritative record from an approved P2.3 decision.

    This pure gate performs no file I/O and does not mutate the decision or
    projection. WITHHOLD, BLOCKED, or inconsistent decisions fail closed.
    """
    if not isinstance(publication_input, AuthoritativePublicationInput):
        raise AuthoritativePublicationGateError(
            "publication_input must be an AuthoritativePublicationInput"
        )

    decision = publication_input.publication_decision
    projection = publication_input.governed_projection

    failures: list[str] = []
    if decision.decision_status != "PUBLISH":
        failures.append("Only a PUBLISH decision may create authoritative publication.")
    if decision.publication_permitted is not True:
        failures.append("publication_permitted must be true.")
    if decision.authoritative_publication_created is not False:
        failures.append("A prior authoritative publication cannot be republished.")
    if decision.certification_outcome != "PASS":
        failures.append("Certification outcome must be PASS.")
    if projection.governed_subject_reference != decision.governed_subject_reference:
        failures.append("Governed subject reference mismatch.")
    if projection.certification_id != decision.certification_id:
        failures.append("Certification ID mismatch.")
    if projection.topic_id != decision.topic_id:
        failures.append("Topic ID mismatch.")
    if projection.topic_version != decision.topic_version:
        failures.append("Topic version mismatch.")
    if projection.limitations != decision.limitations:
        failures.append("Publication limitations must exactly match the decision.")
    if projection.certification_trace_references != decision.certification_trace_references:
        failures.append("Certification trace must exactly match the decision.")
    if projection.evidence_trace_references != decision.evidence_trace_references:
        failures.append("Evidence trace must exactly match the decision.")
    if _contains_boundary(projection.limitations, "bound_not_published"):
        failures.append("bound_not_published cannot cross the publication gate.")
    if _contains_boundary(projection.limitations, "guarantee claim payment"):
        failures.append("Claim-payment guarantee language is not publishable.")

    if failures:
        raise AuthoritativePublicationGateError(" ".join(failures))

    receipt_id = _stable_receipt_id(
        publication_input.publication_id,
        decision.decision_id,
        projection.projection_id,
        projection.governed_subject_reference,
        projection.certification_id,
    )
    return AuthoritativePublicationRecord(
        contract_version=publication_input.contract_version,
        publication_id=publication_input.publication_id,
        decision_id=decision.decision_id,
        governed_subject_reference=projection.governed_subject_reference,
        certification_id=projection.certification_id,
        topic_id=projection.topic_id,
        topic_version=projection.topic_version,
        publication_status=PUBLICATION_STATUS,
        semantic_components=projection.semantic_components,
        limitations=projection.limitations,
        certification_trace_references=projection.certification_trace_references,
        evidence_trace_references=projection.evidence_trace_references,
        publication_authority=publication_input.publication_authority,
        publication_receipt_id=receipt_id,
    )
