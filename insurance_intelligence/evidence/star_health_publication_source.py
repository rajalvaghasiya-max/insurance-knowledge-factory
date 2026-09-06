"""Bounded Star Comprehensive adapter for published answer evidence.

This adapter performs product/topic routing only. It returns existing authoritative
publication plus the matching certified evidence output; the core materializer remains
topic-neutral and revalidates exact publication evidence references.
"""
from __future__ import annotations

from insurance_intelligence.authoritative_publication.star_health import (
    build_star_bariatric_surgery_authoritative_publication,
    build_star_room_rent_authoritative_publication,
)
from insurance_intelligence.evidence.published_materialization import PublishedEvidenceSource
from insurance_intelligence.rule_certification.star_health_bariatric_surgery import (
    build_star_comprehensive_bariatric_surgery_case,
)
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)

STAR_ENTITY = "star_health:star_comprehensive"


def _normalized_requirement_text(requirement) -> str:
    values = (
        getattr(requirement, "evidence_category", ""),
        getattr(requirement, "subject_reference", ""),
        getattr(requirement, "reason", ""),
    )
    return " ".join(str(value).casefold().replace("-", " ") for value in values)


def load_star_published_evidence_source(entity_reference: str, requirement) -> PublishedEvidenceSource | None:
    """Return only already-authoritatively-published Star evidence for the requirement."""
    if entity_reference != STAR_ENTITY:
        return None
    text = _normalized_requirement_text(requirement)
    if "room rent" in text or "room category" in text:
        case = build_star_comprehensive_room_rent_case()
        return PublishedEvidenceSource(
            publication=build_star_room_rent_authoritative_publication(),
            certified_evidence=case.evidence_output,
        )
    if "bariatric" in text:
        case = build_star_comprehensive_bariatric_surgery_case()
        return PublishedEvidenceSource(
            publication=build_star_bariatric_surgery_authoritative_publication(),
            certified_evidence=case.evidence_output,
        )
    return None


__all__ = ["STAR_ENTITY", "load_star_published_evidence_source"]
