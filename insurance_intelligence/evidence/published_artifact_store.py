"""Generic persistence for authoritative publication plus certified evidence artifacts.

Runtime publication lookup must load immutable artifacts rather than reconstruct product-
specific publication/certification builders. This module owns only serialization and
validation; it does not choose products/topics or authorize publication.
"""
from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from insurance_intelligence.contracts.authoritative_publication import (
    AuthoritativePublicationRecord,
    GovernedSemanticComponent,
)
from insurance_intelligence.contracts.evidence import (
    DocumentResolution,
    EntityResolution,
    EvidenceConflict,
    EvidencePackage,
    EvidenceResolverOutput,
    Lineage,
    RequirementResult,
    TraceEvent,
    validate_output,
)
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource


class PublishedArtifactStoreError(ValueError):
    """Raised when persisted published-evidence artifacts are invalid."""


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def persist_published_evidence_source(
    *,
    source: PublishedEvidenceSource,
    publication_path: Path,
    certified_evidence_path: Path,
) -> None:
    """Persist a previously-created published source as deterministic JSON artifacts."""
    if not isinstance(source, PublishedEvidenceSource):
        raise PublishedArtifactStoreError("source must be a PublishedEvidenceSource")
    _write_json(publication_path, asdict(source.publication))
    _write_json(certified_evidence_path, asdict(validate_output(source.certified_evidence)))


def _tuple(value: object, label: str) -> tuple:
    if not isinstance(value, list):
        raise PublishedArtifactStoreError(f"{label} must be a JSON array")
    return tuple(value)


def _publication_from_dict(value: dict) -> AuthoritativePublicationRecord:
    try:
        components = tuple(
            GovernedSemanticComponent(
                component_id=item["component_id"],
                status=item["status"],
                evidence_references=tuple(item["evidence_references"]),
            )
            for item in value["semantic_components"]
        )
        return AuthoritativePublicationRecord(
            contract_version=value["contract_version"],
            publication_id=value["publication_id"],
            decision_id=value["decision_id"],
            governed_subject_reference=value["governed_subject_reference"],
            certification_id=value["certification_id"],
            topic_id=value["topic_id"],
            topic_version=value["topic_version"],
            publication_status=value["publication_status"],
            semantic_components=components,
            limitations=tuple(value["limitations"]),
            certification_trace_references=tuple(value["certification_trace_references"]),
            evidence_trace_references=tuple(value["evidence_trace_references"]),
            publication_authority=value["publication_authority"],
            publication_receipt_id=value["publication_receipt_id"],
            resolved_certification_limitations=tuple(
                value.get("resolved_certification_limitations", [])
            ),
            authorization_id=value.get("authorization_id"),
            authorization_trace_references=tuple(
                value.get("authorization_trace_references", [])
            ),
        )
    except (KeyError, TypeError) as exc:
        raise PublishedArtifactStoreError("invalid authoritative publication artifact") from exc


def _lineage(value: dict) -> Lineage:
    return Lineage(**value)


def _evidence_package(value: dict) -> EvidencePackage:
    material = dict(value)
    material["lineage"] = _lineage(material["lineage"])
    material["retrieval_basis"] = tuple(material["retrieval_basis"])
    return EvidencePackage(**material)


def _requirement_result(value: dict) -> RequirementResult:
    material = dict(value)
    material["matched_evidence_ids"] = tuple(material["matched_evidence_ids"])
    material["rejected_candidate_ids"] = tuple(material["rejected_candidate_ids"])
    return RequirementResult(**material)


def _entity_resolution(value: dict) -> EntityResolution:
    material = dict(value)
    material["alternatives"] = tuple(material["alternatives"])
    material["limitations"] = tuple(material["limitations"])
    return EntityResolution(**material)


def _evidence_conflict(value: dict) -> EvidenceConflict:
    material = dict(value)
    material["evidence_ids"] = tuple(material["evidence_ids"])
    return EvidenceConflict(**material)


def _trace_event(value: dict) -> TraceEvent:
    material = dict(value)
    material["source_paths"] = tuple(material["source_paths"])
    return TraceEvent(**material)


def _evidence_output_from_dict(value: dict) -> EvidenceResolverOutput:
    try:
        output = EvidenceResolverOutput(
            contract_version=value["contract_version"],
            request_id=value["request_id"],
            resolution_id=value["resolution_id"],
            evidence_packages=tuple(_evidence_package(item) for item in value["evidence_packages"]),
            requirement_results=tuple(_requirement_result(item) for item in value["requirement_results"]),
            entity_resolutions=tuple(_entity_resolution(item) for item in value["entity_resolutions"]),
            document_resolutions=tuple(DocumentResolution(**item) for item in value["document_resolutions"]),
            conflicts=tuple(_evidence_conflict(item) for item in value["conflicts"]),
            missing_evidence=tuple(value["missing_evidence"]),
            sufficiency=value["sufficiency"],
            limitations=tuple(value["limitations"]),
            resolution_trace=tuple(_trace_event(item) for item in value["resolution_trace"]),
            resolution_status=value["resolution_status"],
            confidence=value["confidence"],
        )
    except (KeyError, TypeError) as exc:
        raise PublishedArtifactStoreError("invalid certified evidence artifact") from exc
    return validate_output(output)


def load_published_evidence_source(
    *, publication_path: Path, certified_evidence_path: Path
) -> PublishedEvidenceSource:
    """Load and validate one immutable publication/evidence artifact pair."""
    try:
        publication_raw = json.loads(publication_path.read_text(encoding="utf-8"))
        evidence_raw = json.loads(certified_evidence_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishedArtifactStoreError("published evidence artifact could not be loaded") from exc
    if not isinstance(publication_raw, dict) or not isinstance(evidence_raw, dict):
        raise PublishedArtifactStoreError("published evidence artifacts must contain JSON objects")
    return PublishedEvidenceSource(
        publication=_publication_from_dict(publication_raw),
        certified_evidence=_evidence_output_from_dict(evidence_raw),
    )


__all__ = [
    "PublishedArtifactStoreError",
    "load_published_evidence_source",
    "persist_published_evidence_source",
]
