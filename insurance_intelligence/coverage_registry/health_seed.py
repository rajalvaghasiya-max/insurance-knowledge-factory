"""Initial governed Health coverage seed for MO-028A.2.

This seed inventories only coverage already demonstrated by authoritative runtime
artifacts. It does not infer product lifecycle. Until a governed lifecycle source
is added, lifecycle status remains STATUS_UNKNOWN.
"""
from __future__ import annotations

from insurance_intelligence.benefits.activ_one_nxt import (
    ACTIV_ONE_NXT_PRODUCT_VARIANT_ID,
    ACTIV_ONE_NXT_RESTORATION_EVIDENCE,
)
from insurance_intelligence.benefits.activ_one_nxt_room_rent import (
    ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION,
)
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID,
    STAR_COMPREHENSIVE_RESTORATION_EVIDENCE,
)
from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    EvidenceCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
    ProductLifecycleStatus,
)


def _evidence_ids(items: tuple) -> tuple[str, ...]:
    return tuple(item.evidence_reference_id for item in items)


STAR_COMPREHENSIVE_COVERAGE = ProductCoverageRecord(
    product_reference=STAR_COMPREHENSIVE_PRODUCT_VARIANT_ID,
    insurer_id="star_health",
    product_id="star_comprehensive",
    canonical_product_name="Star Comprehensive Insurance Policy",
    uin="SHAHLIP26044V092526",
    lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    evidence_status=EvidenceCoverageStatus.PARTIAL,
    concepts=(
        ConceptCoverageRecord(
            concept_id="restoration",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=_evidence_ids(STAR_COMPREHENSIVE_RESTORATION_EVIDENCE),
            comparison_ready=True,
            decision_support_ready=True,
        ),
        ConceptCoverageRecord(
            concept_id="copayment",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "evidence:star-comprehensive-copayment:governed-statement",
            ),
            comparison_ready=True,
            decision_support_ready=True,
        ),
        ConceptCoverageRecord(
            concept_id="room_rent_restriction",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "evidence:star-comprehensive-room-rent:covered_subject",
                "evidence:star-comprehensive-room-rent:limit_value",
                "evidence:star-comprehensive-room-rent:limit_basis",
                "evidence:star-comprehensive-room-rent:applicability_scope",
                "evidence:star-comprehensive-room-rent:excess_consequence",
            ),
            comparison_ready=True,
            decision_support_ready=True,
        ),
        ConceptCoverageRecord(
            concept_id="waiting_periods",
            status=ConceptCoverageStatus.NOT_AUTOMATED,
            limitations=(
                "Base initial, specific-disease, and PED waiting-period clauses are not yet governed for automation.",
            ),
        ),
    ),
)


ACTIV_ONE_NXT_COVERAGE = ProductCoverageRecord(
    product_reference=ACTIV_ONE_NXT_PRODUCT_VARIANT_ID,
    insurer_id="aditya_birla_health",
    product_id="activ_one",
    canonical_product_name="Activ One NXT",
    uin="ADIHLIP24097V012324",
    lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    evidence_status=EvidenceCoverageStatus.PARTIAL,
    concepts=(
        ConceptCoverageRecord(
            concept_id="restoration",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=_evidence_ids(ACTIV_ONE_NXT_RESTORATION_EVIDENCE),
            comparison_ready=True,
            decision_support_ready=True,
        ),
        ConceptCoverageRecord(
            concept_id="room_rent_restriction",
            status=ConceptCoverageStatus.SOURCE_LIMITED,
            evidence_reference_ids=(
                ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION.evidence_reference_id,
            ),
            comparison_ready=False,
            decision_support_ready=False,
            limitations=ACTIV_ONE_NXT_ROOM_RENT_PUBLICATION.limitations,
        ),
        ConceptCoverageRecord(
            concept_id="waiting_periods",
            status=ConceptCoverageStatus.NOT_AUTOMATED,
            limitations=(
                "Waiting-period semantics have not yet been governed for Activ One NXT decision support.",
            ),
        ),
    ),
)


HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(
    (
        STAR_COMPREHENSIVE_COVERAGE,
        ACTIV_ONE_NXT_COVERAGE,
    )
)


__all__ = [
    "ACTIV_ONE_NXT_COVERAGE",
    "HEALTH_COVERAGE_REGISTRY",
    "STAR_COMPREHENSIVE_COVERAGE",
]
