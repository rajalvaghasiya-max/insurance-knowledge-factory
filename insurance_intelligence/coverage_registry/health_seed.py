"""Current Health coverage seed built only from governed, certified repository state.

This seed is intentionally conservative. It records local concept certification but
never promotes that fact into comparison readiness, decision-support readiness, or
product lifecycle status without separate governed evidence.
"""
from __future__ import annotations

from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageRecord,
    ConceptCoverageStatus,
    EvidenceCoverageStatus,
    InsuranceIntelligenceCoverageRegistry,
    ProductCoverageRecord,
    ProductLifecycleStatus,
)


STAR_COMPREHENSIVE_COVERAGE = ProductCoverageRecord(
    product_reference="star_health:star_comprehensive:SHAHLIP26044V092526",
    insurer_id="star_health",
    product_id="star_comprehensive",
    canonical_product_name="Star Comprehensive Insurance Policy",
    uin="SHAHLIP26044V092526",
    lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    evidence_status=EvidenceCoverageStatus.PARTIAL,
    concepts=(
        ConceptCoverageRecord(
            concept_id="copayment",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "docs/architecture/star_health_star_comprehensive_conditional_copayment_binding_spec.json",
                "docs/architecture/star_health_star_comprehensive_conditional_copayment_canonical_projection_spec.json",
                "tests/insurance_intelligence/test_star_conditional_copayment_certification.py",
            ),
            comparison_ready=False,
            decision_support_ready=False,
        ),
    ),
)


BAJAJ_MY_HEALTH_CARE_V2_COVERAGE = ProductCoverageRecord(
    product_reference="bajaj_allianz_general:my_health_care:BAJHLIP26074V022526",
    insurer_id="bajaj_allianz_general",
    product_id="my_health_care",
    canonical_product_name="My Health Care Plan",
    uin="BAJHLIP26074V022526",
    lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    evidence_status=EvidenceCoverageStatus.PARTIAL,
    concepts=(
        ConceptCoverageRecord(
            concept_id="copayment",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "docs/architecture/bajaj_my_health_care_v2_copayment_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_copayment_canonical_projection_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_copayment_certification_spec.json",
            ),
            comparison_ready=False,
            decision_support_ready=False,
        ),
        ConceptCoverageRecord(
            concept_id="waiting_period",
            status=ConceptCoverageStatus.PARTIAL,
            evidence_reference_ids=(
                "docs/architecture/bajaj_my_health_care_v2_waiting_period_pressure_inventory_2026-08-22.json",
                "docs/architecture/bajaj_my_health_care_v2_initial_waiting_period_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_initial_waiting_period_qualification_2026-08-22.json",
            ),
            comparison_ready=False,
            decision_support_ready=False,
            limitations=(
                "The Plan 1 initial waiting period is resolved to 30 days from exact current-v2 mechanism and Schedule-table evidence, but waiting-period certification remains incomplete.",
                "Enhanced-Sum-Insured reapplication is evidenced but does not yet have a typed runtime representation in WaitingPeriodMechanic.",
                "PED, specified-disease/procedure, maternity, and baby-care waiting periods remain unresolved Schedule-dependent families for this coverage milestone.",
            ),
        ),
    ),
)


HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(
    (
        BAJAJ_MY_HEALTH_CARE_V2_COVERAGE,
        STAR_COMPREHENSIVE_COVERAGE,
    )
)


__all__ = [
    "BAJAJ_MY_HEALTH_CARE_V2_COVERAGE",
    "HEALTH_COVERAGE_REGISTRY",
    "STAR_COMPREHENSIVE_COVERAGE",
]
