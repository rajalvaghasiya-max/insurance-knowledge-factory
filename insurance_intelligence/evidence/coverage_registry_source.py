"""Coverage-registry-backed lookup for published answer evidence.

The coverage registry remains the authority for governed product/concept coverage. After
product resolution, this lookup discovers frozen authoritative-publication artifacts from
the product's governed publication directory and loads the matching published evidence
source. Product/topic-specific Python branches are not permitted here.
"""
from __future__ import annotations

from pathlib import Path
import re

from insurance_intelligence.coverage_registry.contracts import (
    InsuranceIntelligenceCoverageRegistry,
)
from insurance_intelligence.evidence.published_artifact_store import (
    load_published_evidence_source,
)
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource


class CoverageRegistryPublishedSourceError(ValueError):
    """Raised when governed publication artifacts are ambiguous or invalid."""


def _normalize(value: object) -> str:
    text = str(value).casefold().replace("_", " ").replace("-", " ")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _requirement_text(requirement: object) -> str:
    return _normalize(
        " ".join(
            str(getattr(requirement, field, ""))
            for field in ("evidence_category", "subject_reference", "reason")
        )
    )


def _entity_key(product) -> str:
    return f"{product.insurer_id}:{product.product_id}"


def _publication_directory(root: Path, entity_reference: str) -> Path:
    return (
        root
        / "knowledge"
        / "factory"
        / "registry_backed"
        / entity_reference.replace(":", "_")
        / "publication"
    )


def _descriptor_from_publication_id(publication_id: str) -> str:
    if not isinstance(publication_id, str) or not publication_id.strip():
        raise CoverageRegistryPublishedSourceError(
            "authoritative publication must declare a non-empty publication_id"
        )
    return _normalize(publication_id.rsplit(":", 1)[-1])


def _candidate_sources(
    *,
    root: Path,
    entity_reference: str,
) -> tuple[PublishedEvidenceSource, ...]:
    directory = _publication_directory(root, entity_reference)
    if not directory.is_dir():
        return ()
    sources: list[PublishedEvidenceSource] = []
    for publication_path in sorted(directory.glob("*_authoritative_publication.json")):
        evidence_path = publication_path.with_name(
            publication_path.name.replace(
                "_authoritative_publication.json",
                "_certified_evidence.json",
            )
        )
        if not evidence_path.is_file():
            raise CoverageRegistryPublishedSourceError(
                f"missing certified evidence artifact for {publication_path.as_posix()}"
            )
        sources.append(
            load_published_evidence_source(
                publication_path=publication_path,
                certified_evidence_path=evidence_path,
            )
        )
    return tuple(sources)


def build_coverage_registry_published_source_lookup(
    *,
    registry: InsuranceIntelligenceCoverageRegistry,
    repository_root: Path,
):
    """Build a topic-neutral PublishedSourceLookup from governed product publication artifacts."""
    if not isinstance(registry, InsuranceIntelligenceCoverageRegistry):
        raise TypeError("registry must be an InsuranceIntelligenceCoverageRegistry")
    root = Path(repository_root)

    def lookup(entity_reference: str, requirement: object) -> PublishedEvidenceSource | None:
        products = tuple(
            product for product in registry.products if _entity_key(product) == entity_reference
        )
        if len(products) != 1:
            return None
        text = _requirement_text(requirement)
        matches = tuple(
            source
            for source in _candidate_sources(root=root, entity_reference=entity_reference)
            if (
                descriptor := _descriptor_from_publication_id(
                    source.publication.publication_id
                )
            )
            and descriptor in text
        )
        if not matches:
            return None
        if len(matches) != 1:
            raise CoverageRegistryPublishedSourceError(
                "multiple authoritative publication artifacts matched one evidence requirement"
            )
        return matches[0]

    return lookup


__all__ = [
    "CoverageRegistryPublishedSourceError",
    "build_coverage_registry_published_source_lookup",
]
