"""Deterministic authoritative-publication gate (P2.4)."""

from __future__ import annotations

from hashlib import sha256
import re

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


def _contains_affirmative_claim_payment_guarantee(values: tuple[str, ...]) -> bool:
    """Detect affirmative claim-payment guarantees without blocking disclaimers."""
    affirmative_patterns = (
        re.compile(r"\bguarantee(?:s|d)?\s+(?:the\s+)?claim\s+payment\b"),
        re.compile(r"\bclaim\s+payment\s+(?:is|will\s+be)\s+guaranteed\b"),
    )
    negation_pattern = re.compile(
        r"\b(?:does\s+not|do\s+not|did\s+not|cannot|can\s+not|will\s+not|not)\s+$"
    )
    for value in values:
        normalized = " ".join(value.casefold().split())
        for pattern in affirmative_patterns:
            for match in pattern.finditer(normalized):
                prefix = normalized[max(0, match.start() - 24) : match.start()]
                if not negation_pattern.search(prefix):
                    return True
    return False


def _stable_receipt_id(*parts: str) -> str:
    digest = sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"publication_receipt_{digest}"


def create_authoritative_publication(
    publication_input: AuthoritativePublicationInput,
) -> AuthoritativePublicationRecord:
    """Create an immutable authoritative record from an approved P2.3 decision.

    This pure gate performs no file I/O and does not mutate the decision or projection.
    WITHHOLD, BLOCKED, inconsistent decisions, or incomplete authorization lineage fail
    closed.
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
    if _contains_affirmative_claim_payment_guarantee(projection.limitations):
        failures.append("Claim-payment guarantee language is not publishable.")

    if decision.resolved_certification_limitations:
        if not decision.authorization_id:
            failures.append("Resolved certification limitations require authorization_id.")
        if not decision.authorization_trace_references:
            failures.append(
                "Resolved certification limitations require authorization trace references."
            )
    elif decision.authorization_id or decision.authorization_trace_references:
        failures.append(
            "Publication authorization metadata cannot be present without resolved certification limitations."
        )

    if failures:
        raise AuthoritativePublicationGateError(" ".join(failures))

    receipt_parts = [
        publication_input.publication_id,
        decision.decision_id,
        projection.projection_id,
        projection.governed_subject_reference,
        projection.certification_id,
    ]
    if decision.authorization_id:
        receipt_parts.append(decision.authorization_id)
    receipt_id = _stable_receipt_id(*receipt_parts)
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
        resolved_certification_limitations=decision.resolved_certification_limitations,
        authorization_id=decision.authorization_id,
        authorization_trace_references=decision.authorization_trace_references,
    )
