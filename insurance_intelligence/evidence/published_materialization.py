"""Materialize answer-admissible evidence from authoritative publication.

The authoritative publication record is the admission proof; the certified evidence
output remains the material source for claim text and source lineage. Structured
semantic attributes are projected from publication components onto the corresponding
EvidencePackage without parsing or reinterpreting claim text.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
)
from insurance_intelligence.contracts.evidence import (
    EvidencePackage,
    EvidenceResolverOutput,
    RequirementResult,
)
from insurance_intelligence.contracts.semantic import (
    GovernedSemanticAttribute,
    build_governed_semantic_attribute,
)
from insurance_intelligence.topic_completeness.catalogue import build_default_topic_registry
from insurance_intelligence.topic_completeness.registry import TopicCompletenessRegistryError
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


def _attributes_for_evidence(
    publication: AuthoritativePublicationRecord,
    evidence_id: str,
) -> tuple[GovernedSemanticAttribute, ...]:
    by_key: dict[str, GovernedSemanticAttribute] = {}
    for component in publication.semantic_components:
        for attribute in component.semantic_attributes:
            if evidence_id not in attribute.evidence_references:
                continue
            existing = by_key.get(attribute.key)
            if existing is not None and existing != attribute:
                raise PublishedEvidenceMaterializationError(
                    f"conflicting published semantic attribute {attribute.key!r} for evidence {evidence_id!r}"
                )
            by_key[attribute.key] = attribute
    return tuple(by_key[key] for key in sorted(by_key))


def _runtime_evidence_id(*, requirement_id: str, certified_evidence_id: str) -> str:
    """Create a stable runtime identity for one certified item in one requirement.

    Certified evidence identity remains immutable publication provenance. Runtime
    EvidencePackage identity is requirement-scoped because the same authoritative
    source may legitimately satisfy more than one planner requirement in one
    resolution and EvidenceResolverOutput requires globally unique package IDs.
    """
    digest = sha256(
        f"{requirement_id}\x1f{certified_evidence_id}".encode("utf-8")
    ).hexdigest()[:20]
    return f"published_ev_{digest}"


def _answer_roles_by_evidence(
    publication: AuthoritativePublicationRecord,
) -> dict[str, str]:
    """Derive answer roles only when published topic semantics are unambiguous.

    One and only one published required component may become PRIMARY. Published
    optional components become QUALIFYING. Unknown components or multiple required
    components deliberately produce no inferred answer role.
    """
    try:
        definition = build_default_topic_registry().get(
            publication.topic_id,
            publication.topic_version,
        )
    except TopicCompletenessRegistryError:
        return {}

    component_defs = {item.component_id: item for item in definition.components}
    published = tuple(publication.semantic_components)
    if any(item.component_id not in component_defs for item in published):
        return {}

    required = tuple(
        item
        for item in published
        if component_defs[item.component_id].required
    )
    if len(required) != 1:
        return {}

    primary_component_id = required[0].component_id
    roles: dict[str, set[str]] = {}
    for component in published:
        role = (
            "PRIMARY"
            if component.component_id == primary_component_id
            else "QUALIFYING"
        )
        for evidence_id in component.evidence_references:
            roles.setdefault(evidence_id, set()).add(role)

    return {
        evidence_id: next(iter(values))
        for evidence_id, values in roles.items()
        if len(values) == 1
    }


def _runtime_attributes(
    *,
    publication: AuthoritativePublicationRecord,
    certified_evidence_id: str,
    runtime_ids: dict[str, str],
    answer_roles: dict[str, str],
) -> tuple[GovernedSemanticAttribute, ...]:
    attributes = [
        replace(
            attribute,
            evidence_references=tuple(
                runtime_ids.get(reference, reference)
                for reference in attribute.evidence_references
            ),
        )
        for attribute in _attributes_for_evidence(publication, certified_evidence_id)
    ]
    role = answer_roles.get(certified_evidence_id)
    if role is not None and not any(item.key == "answer_role" for item in attributes):
        attributes.append(
            build_governed_semantic_attribute(
                key="answer_role",
                value=role,
                evidence_references=(runtime_ids[certified_evidence_id],),
            )
        )
    return tuple(sorted(attributes, key=lambda item: item.key))


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

    runtime_ids = {
        evidence_id: _runtime_evidence_id(
            requirement_id=requirement_id,
            certified_evidence_id=evidence_id,
        )
        for evidence_id in published_ids
    }
    answer_roles = _answer_roles_by_evidence(publication)
    packages = tuple(
        replace(
            by_id[evidence_id],
            evidence_id=runtime_ids[evidence_id],
            requirement_id=requirement_id,
            subject_reference=subject_reference,
            semantic_attributes=_runtime_attributes(
                publication=publication,
                certified_evidence_id=evidence_id,
                runtime_ids=runtime_ids,
                answer_roles=answer_roles,
            ),
            retrieval_basis=by_id[evidence_id].retrieval_basis
            + (
                "authoritative_publication_admission",
                publication.publication_id,
                publication.publication_receipt_id,
                f"certified_evidence_id:{evidence_id}",
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
