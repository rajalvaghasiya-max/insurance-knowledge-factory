"""Materialize answer-admissible evidence from authoritative publication.

The authoritative publication record is the admission proof; the certified evidence
output remains the material source for claim text and source lineage. This module does
not infer facts, publish knowledge, or perform topic-specific routing.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
)
from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    RequirementResult,
)
from insurance_intelligence.evidence.admission import (
    USER_ANSWER,
    evaluate_publication_admission,
)


class PublishedEvidenceMaterializationError(ValueError):
    """Raised when authoritative publication cannot be reconciled to certified evidence."""


@dataclass(frozen=True)
class PublishedEvidenceSource:
    publication: AuthoritativePublicationRecord
    certified_evidence: EvidenceResolverOutput


def materialize_published_requirement(
    *,
    source: PublishedEvidenceSource,
    requirement_id: str,
    subject_reference: str,
) -> tuple[tuple[EvidencePackage, ...], RequirementResult]:
    """Project exactly published evidence references into one runtime requirement."""
    if not isinstance(source, PublishedEvidenceSource):
        raise PublishedEvidenceMaterializationError("source must be a PublishedEvidenceSource")
    publication = source.publication
    evidence_output = source.certified_evidence
    admission = evaluate_publication_admission(
        evidence_use=USER_ANSWER,
        publication=publication,
        topic_id=publication.topic_id,
    )
    if not admission.admitted:
        raise PublishedEvidenceMaterializationError(admission.basis)
    if evidence_output.resolution_status not in {"RESOLVED", "RESOLVED_WITH_LIMITATIONS"}:
        raise PublishedEvidenceMaterializationError("certified evidence output is not resolved")

    by_id = {item.evidence_id: item for item in evidence_output.evidence_packages}
    published_ids: list[str] = []
    for component in publication.semantic_components:
        if component.status != "SATISFIED":
            raise PublishedEvidenceMaterializationError(
                f"published semantic component {component.component_id!r} is not SATISFIED"
            )
        for evidence_id in component.evidence_references:
            if evidence_id not in by_id:
                raise PublishedEvidenceMaterializationError(
                    f"authoritative publication references missing evidence {evidence_id!r}"
                )
            if evidence_id not in published_ids:
                published_ids.append(evidence_id)

    if not published_ids:
        raise PublishedEvidenceMaterializationError("authoritative publication contains no evidence references")

    packages = tuple(
        replace(
            by_id[evidence_id],
            requirement_id=requirement_id,
            subject_reference=subject_reference,
            retrieval_basis=by_id[evidence_id].retrieval_basis
            + (
                "authoritative_publication_admission",
                publication.publication_id,
                publication.publication_receipt_id,
            ),
        )
        for evidence_id in published_ids
    )
    requirement = RequirementResult(
        requirement_id=requirement_id,
        status="SATISFIED",
        matched_evidence_ids=tuple(item.evidence_id for item in packages),
        rejected_candidate_ids=(),
        missing_reason=None,
        authority_satisfied=True,
        version_satisfied=True,
        lineage_satisfied=all(item.lineage.lineage_status == "VERIFIED" for item in packages),
        conflict_status="NONE",
        confidence=min(item.confidence for item in packages),
    )
    return packages, requirement


__all__ = [
    "PublishedEvidenceMaterializationError",
    "PublishedEvidenceSource",
    "materialize_published_requirement",
]
