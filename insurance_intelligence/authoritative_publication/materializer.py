"""Generic composition of certified evidence into authoritative publication.

This module joins existing certification, publication-decision, authoritative-gate and
published-evidence contracts. It contains no insurer or topic routing and performs no
file I/O. Product/topic semantics must already be explicit in governed certification,
semantic-component and evidence objects supplied by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.authoritative_publication.gate import (
    create_authoritative_publication,
)
from insurance_intelligence.contracts.authoritative_publication import (
    GovernedSemanticComponent,
    build_authoritative_publication_input,
    build_governed_publication_projection,
)
from insurance_intelligence.contracts.evidence import EvidenceResolverOutput, validate_output
from insurance_intelligence.contracts.publication_decision import (
    PublicationBoundaryAuthorization,
    build_publication_decision_input,
)
from insurance_intelligence.contracts.rule_certification import RuleCertificationResult
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource
from insurance_intelligence.publication_decision.evaluator import evaluate_publication_decision


class AuthoritativePublicationMaterializationError(ValueError):
    """Raised when governed material cannot safely cross the publication pipeline."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthoritativePublicationMaterializationError(
            f"{label} must be non-empty text"
        )
    return value.strip()


def _unique_text(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if not result:
        raise AuthoritativePublicationMaterializationError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise AuthoritativePublicationMaterializationError(
            f"{label} must not contain duplicates"
        )
    return result


@dataclass(frozen=True)
class AuthoritativePublicationMaterializationRequest:
    decision_id: str
    publication_id: str
    projection_id: str
    decision_reasons: tuple[str, ...]
    decision_authority: str
    publication_authority: str
    limitations: tuple[str, ...]
    semantic_components: tuple[GovernedSemanticComponent, ...]
    boundary_authorization: PublicationBoundaryAuthorization | None = None


def build_authoritative_publication_materialization_request(
    *,
    decision_id: str,
    publication_id: str,
    projection_id: str,
    decision_reasons: Sequence[str],
    decision_authority: str,
    publication_authority: str,
    limitations: Sequence[str],
    semantic_components: Sequence[GovernedSemanticComponent],
    boundary_authorization: PublicationBoundaryAuthorization | None = None,
) -> AuthoritativePublicationMaterializationRequest:
    components = tuple(semantic_components)
    if not components:
        raise AuthoritativePublicationMaterializationError(
            "semantic_components must not be empty"
        )
    if not all(isinstance(item, GovernedSemanticComponent) for item in components):
        raise AuthoritativePublicationMaterializationError(
            "semantic_components must contain GovernedSemanticComponent values"
        )
    component_ids = [item.component_id for item in components]
    if len(component_ids) != len(set(component_ids)):
        raise AuthoritativePublicationMaterializationError(
            "semantic component IDs must be unique"
        )
    if boundary_authorization is not None and not isinstance(
        boundary_authorization, PublicationBoundaryAuthorization
    ):
        raise AuthoritativePublicationMaterializationError(
            "boundary_authorization must be a PublicationBoundaryAuthorization or None"
        )
    return AuthoritativePublicationMaterializationRequest(
        decision_id=_text(decision_id, "decision_id"),
        publication_id=_text(publication_id, "publication_id"),
        projection_id=_text(projection_id, "projection_id"),
        decision_reasons=_unique_text(decision_reasons, "decision_reasons"),
        decision_authority=_text(decision_authority, "decision_authority"),
        publication_authority=_text(publication_authority, "publication_authority"),
        limitations=tuple(_text(value, "limitations[]") for value in limitations),
        semantic_components=components,
        boundary_authorization=boundary_authorization,
    )


def _evidence_trace(
    components: tuple[GovernedSemanticComponent, ...],
) -> tuple[str, ...]:
    trace: list[str] = []
    seen: set[str] = set()
    for component in components:
        for reference in component.evidence_references:
            if reference not in seen:
                seen.add(reference)
                trace.append(reference)
    if not trace:
        raise AuthoritativePublicationMaterializationError(
            "semantic components must reference governed evidence"
        )
    return tuple(trace)


def materialize_authoritative_published_evidence(
    *,
    certification: RuleCertificationResult,
    certified_evidence: EvidenceResolverOutput,
    request: AuthoritativePublicationMaterializationRequest,
) -> PublishedEvidenceSource:
    """Run the existing publication authorities and return one immutable published source."""
    if not isinstance(certification, RuleCertificationResult):
        raise AuthoritativePublicationMaterializationError(
            "certification must be a RuleCertificationResult"
        )
    if not isinstance(request, AuthoritativePublicationMaterializationRequest):
        raise AuthoritativePublicationMaterializationError(
            "request must be an AuthoritativePublicationMaterializationRequest"
        )
    evidence = validate_output(certified_evidence)

    if certification.outcome != "PASS":
        raise AuthoritativePublicationMaterializationError(
            "only PASS certification may be materialized for publication"
        )
    if certification.request_id != evidence.request_id:
        raise AuthoritativePublicationMaterializationError(
            "certification request id must match certified evidence"
        )
    if certification.resolution_id != evidence.resolution_id:
        raise AuthoritativePublicationMaterializationError(
            "certification resolution id must match certified evidence"
        )

    checks = {item.component_id: item for item in certification.component_checks}
    evidence_ids = {item.evidence_id for item in evidence.evidence_packages}
    for component in request.semantic_components:
        if component.status != "SATISFIED":
            raise AuthoritativePublicationMaterializationError(
                f"publication component is not SATISFIED: {component.component_id}"
            )
        check = checks.get(component.component_id)
        if check is None or check.passed is not True:
            raise AuthoritativePublicationMaterializationError(
                f"publication component was not certified: {component.component_id}"
            )
        missing = tuple(
            reference
            for reference in component.evidence_references
            if reference not in evidence_ids
        )
        if missing:
            raise AuthoritativePublicationMaterializationError(
                "publication component references missing certified evidence: "
                + ", ".join(missing)
            )

    authorization = request.boundary_authorization
    if authorization is not None:
        if authorization.governed_subject_reference != certification.governed_subject_reference:
            raise AuthoritativePublicationMaterializationError(
                "boundary authorization governed subject must match certification"
            )
        if authorization.certification_id != certification.certification_id:
            raise AuthoritativePublicationMaterializationError(
                "boundary authorization certification id must match certification"
            )

    evidence_trace = _evidence_trace(request.semantic_components)
    decision = evaluate_publication_decision(
        build_publication_decision_input(
            decision_id=request.decision_id,
            governed_subject_reference=certification.governed_subject_reference,
            certification_result=certification,
            requested_status="PUBLISH",
            decision_reasons=request.decision_reasons,
            limitations=request.limitations,
            evidence_trace_references=evidence_trace,
            decision_authority=request.decision_authority,
            boundary_authorization=authorization,
        )
    )
    if decision.decision_status != "PUBLISH" or decision.publication_permitted is not True:
        detail = "; ".join(decision.failures) or decision.decision_status
        raise AuthoritativePublicationMaterializationError(
            "publication decision did not permit authoritative publication: " + detail
        )

    projection = build_governed_publication_projection(
        projection_id=request.projection_id,
        governed_subject_reference=certification.governed_subject_reference,
        certification_id=certification.certification_id,
        topic_id=certification.topic_id,
        topic_version=certification.topic_version,
        semantic_components=request.semantic_components,
        limitations=decision.limitations,
        evidence_trace_references=decision.evidence_trace_references,
        certification_trace_references=decision.certification_trace_references,
    )
    publication = create_authoritative_publication(
        build_authoritative_publication_input(
            publication_id=request.publication_id,
            publication_decision=decision,
            governed_projection=projection,
            publication_authority=request.publication_authority,
        )
    )
    return PublishedEvidenceSource(
        publication=publication,
        certified_evidence=evidence,
    )


__all__ = [
    "AuthoritativePublicationMaterializationError",
    "AuthoritativePublicationMaterializationRequest",
    "build_authoritative_publication_materialization_request",
    "materialize_authoritative_published_evidence",
]
