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
        ConceptCoverageRecord(
            concept_id="waiting_period",
            status=ConceptCoverageStatus.PARTIAL,
            evidence_reference_ids=(
                "docs/architecture/STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_MANUFACTURING_CLOSURE.md",
                "insurance_intelligence/rule_certification/star_health_initial_waiting_period.py",
                "docs/architecture/star_health_star_comprehensive_ped_waiting_period_binding_spec.json",
                "docs/architecture/star_health_star_comprehensive_ped_material_rules_spec.json",
                "tests/insurance_intelligence/test_star_comprehensive_ped_waiting_period.py",
            ),
            comparison_ready=False,
            decision_support_ready=False,
            limitations=(
                "The standard 30-day initial waiting-period mechanic is certified complete from current primary-legal evidence; exact first-active calendar arithmetic remains withheld.",
                "The standard PED mechanic is certified at 36 months with portability credit, enhanced-Sum-Insured reapplication, and the post-wait declaration-and-insurer-acceptance condition preserved.",
                "The optional PED waiting-period buy-back from 36 months to 12 months is not certified by this slice and requires separate governed treatment.",
                "The specified-disease/procedure waiting-period family remains outstanding, so the overall waiting_period concept remains PARTIAL.",
            ),
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
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "docs/architecture/bajaj_my_health_care_v2_waiting_period_pressure_inventory_2026-08-22.json",
                "docs/architecture/bajaj_my_health_care_v2_initial_waiting_period_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_initial_waiting_period_qualification_2026-08-22.json",
                "docs/architecture/bajaj_my_health_care_v2_ped_waiting_period_option_domain_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_specific_disease_waiting_period_option_domain_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_waiting_period_option_domain_certification_closure_2026-08-22.json",
                "docs/architecture/bajaj_my_health_care_v2_maternity_waiting_period_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_baby_care_waiting_period_binding_spec.json",
                "docs/architecture/bajaj_my_health_care_v2_waiting_period_concept_certification_closure_2026-08-22.json",
            ),
            comparison_ready=False,
            decision_support_ready=False,
            limitations=(
                "The Plan 1 initial waiting-period mechanic is certified complete: 30 days, Policy-Schedule-selected origin, accident and continuity exceptions, and enhanced-Sum-Insured reapplication are preserved.",
                "PED and specified-disease/procedure authoritative 1/2/3-year Schedule option domains and their material mechanics are certified complete; the actual customer-specific selected duration remains unresolved until Policy Schedule evidence is available.",
                "Maternity and baby-care waiting periods are certified complete at 36 months with the governed long-term-upfront-premium reduction to 24 months; maternity also preserves the ectopic-pregnancy exception.",
                "Concept certification does not authorize publication, comparison readiness, decision-support readiness, claim-payment prediction, or customer-specific Schedule inference.",
            ),
        ),
    ),
)


HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE = ProductCoverageRecord(
    product_reference="hdfc_ergo:optima_secure:HDFHLIP26058V082526",
    insurer_id="hdfc_ergo",
    product_id="optima_secure",
    canonical_product_name="my: Optima Secure",
    uin="HDFHLIP26058V082526",
    lifecycle_status=ProductLifecycleStatus.STATUS_UNKNOWN,
    evidence_status=EvidenceCoverageStatus.PARTIAL,
    concepts=(
        ConceptCoverageRecord(
            concept_id="waiting_period",
            status=ConceptCoverageStatus.CERTIFIED,
            evidence_reference_ids=(
                "docs/architecture/hdfc_ergo_optima_secure_v8_initial_waiting_period_binding_spec.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_initial_waiting_period_certification_closure_2026-08-22.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_ped_waiting_period_full_mechanics_binding_spec.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_ped_full_mechanics_certification_closure_2026-08-22.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_specified_disease_waiting_period_binding_spec.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_specified_disease_material_rules_spec.json",
                "docs/architecture/hdfc_ergo_optima_secure_v8_waiting_period_concept_certification_closure_2026-08-22.json",
            ),
            comparison_ready=False,
            decision_support_ready=False,
            limitations=(
                "The base-policy initial waiting period is certified complete at 30 days with accident and continuity exceptions and enhanced-Sum-Insured reapplication.",
                "PED authoritative 12/24/36-month Schedule options and multispan material mechanics are certified complete; the customer-specific selected PED duration remains unresolved until Policy Schedule evidence is available.",
                "Specified-disease/procedure waiting period is certified complete at a product-fixed 24 months with accident exception, portability credit, enhanced-Sum-Insured reapplication, longer-of-PED relationship, and the additional listed-condition applicability rule.",
                "This concept certification covers the governed base-policy waiting-period families only; separate add-on waiting periods such as Parenthood are not certified or inferred here.",
                "Concept certification does not authorize publication, comparison readiness, decision-support readiness, claim-payment prediction, or underwriting-specific waiting-period inference.",
            ),
        ),
    ),
)


HEALTH_COVERAGE_REGISTRY = InsuranceIntelligenceCoverageRegistry(
    (
        BAJAJ_MY_HEALTH_CARE_V2_COVERAGE,
        HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE,
        STAR_COMPREHENSIVE_COVERAGE,
    )
)


__all__ = [
    "BAJAJ_MY_HEALTH_CARE_V2_COVERAGE",
    "HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE",
    "HEALTH_COVERAGE_REGISTRY",
    "STAR_COMPREHENSIVE_COVERAGE",
]
