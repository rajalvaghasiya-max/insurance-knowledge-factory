"""Coverage-registry-backed lookup for published answer evidence.

The coverage registry already owns product/concept/evidence inventory. Published runtime
lookup reuses that inventory by interpreting prefixed immutable artifact references from
ConceptCoverageRecord.evidence_reference_ids. Product/topic-specific Python branches are
not permitted here.
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

PUBLICATION_ARTIFACT_PREFIX = "authoritative_publication_artifact:"
CERTIFIED_EVIDENCE_ARTIFACT_PREFIX = "certified_evidence_artifact:"


class CoverageRegistryPublishedSourceError(ValueError):
    """Raised when published-artifact registry metadata is ambiguous or invalid."""


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


def _artifact_reference(values: tuple[str, ...], prefix: str) -> str | None:
    matches = tuple(item[len(prefix) :] for item in values if item.startswith(prefix))
    if not matches:
        return None
    if len(matches) != 1 or not matches[0].strip():
        raise CoverageRegistryPublishedSourceError(
            f"concept must declare exactly one non-empty {prefix.rstrip(':')} reference"
        )
    return matches[0]


def build_coverage_registry_published_source_lookup(
    *,
    registry: InsuranceIntelligenceCoverageRegistry,
    repository_root: Path,
):
    """Build a topic-neutral PublishedSourceLookup from the existing coverage registry."""
    if not isinstance(registry, InsuranceIntelligenceCoverageRegistry):
        raise TypeError("registry must be an InsuranceIntelligenceCoverageRegistry")
    root = Path(repository_root)

    def lookup(entity_reference: str, requirement: object) -> PublishedEvidenceSource | None:
        products = tuple(
            product for product in registry.products if _entity_key(product) == entity_reference
        )
        if len(products) != 1:
            return None
        product = products[0]
        text = _requirement_text(requirement)
        matched = tuple(
            concept
            for concept in product.concepts
            if _normalize(concept.concept_id) and _normalize(concept.concept_id) in text
        )
        if len(matched) != 1:
            return None
        concept = matched[0]
        publication_ref = _artifact_reference(
            concept.evidence_reference_ids, PUBLICATION_ARTIFACT_PREFIX
        )
        evidence_ref = _artifact_reference(
            concept.evidence_reference_ids, CERTIFIED_EVIDENCE_ARTIFACT_PREFIX
        )
        if publication_ref is None or evidence_ref is None:
            return None
        return load_published_evidence_source(
            publication_path=root / publication_ref,
            certified_evidence_path=root / evidence_ref,
        )

    return lookup


__all__ = [
    "CERTIFIED_EVIDENCE_ARTIFACT_PREFIX",
    "CoverageRegistryPublishedSourceError",
    "PUBLICATION_ARTIFACT_PREFIX",
    "build_coverage_registry_published_source_lookup",
]
