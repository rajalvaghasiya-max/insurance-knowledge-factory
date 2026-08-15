from pathlib import Path

from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.orchestration.star_comprehensive_knowledge_build import (
    PRODUCT_REFERENCE,
    TOPIC,
    build_star_comprehensive_copay_snapshot,
)


REQUIRED_RESTORATION_DIMENSIONS = {
    "restoration_percentage",
    "restoration_count_per_policy_period",
    "trigger_requirement",
    "trigger_timing",
    "same_hospitalization_use",
    "subsequent_hospitalization_use",
    "same_illness_use",
    "covered_section_scope",
    "relapse_window_days",
    "policy_year_reset",
    "carry_over_between_policy_years",
    "floater_operation",
}


def test_star_comprehensive_conditional_copay_chain_is_currently_certifiable() -> None:
    result = build_star_comprehensive_copay_snapshot(
        repository_root=Path("."),
        build_request_id="ar30g0-pressure-qualification",
    )

    assert result.status == "CERTIFIED"
    assert result.product_reference == PRODUCT_REFERENCE == "star_health:star_comprehensive"
    assert result.topic == TOPIC == "conditional_copayment"
    assert len(result.receipts) == 7
    assert {receipt.stage for receipt in result.receipts} == {
        "SOURCE_REGISTRATION",
        "DOCUMENT_IDENTITY",
        "DOCUMENT_CLASSIFICATION",
        "LEGAL_BINDING",
        "CANONICAL_PROJECTION",
        "PUBLICATION_DECISION",
        "AUTHORITATIVE_PUBLICATION",
    }
    assert result.assertion_ids
    assert result.publication_ids
    assert result.limitations == (
        "Snapshot certifies the reviewed conditional co-payment artifact chain only.",
    )


def test_star_comprehensive_restoration_is_governed_and_preserves_dense_mechanics() -> None:
    implementation = STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION

    assert implementation.review_status is ReviewStatus.APPROVED
    assert implementation.publication_status is PublicationStatus.PUBLISHED
    assert implementation.is_governed_for_use is True

    mechanics = {item.dimension_id: item for item in implementation.mechanics}
    assert REQUIRED_RESTORATION_DIMENSIONS <= set(mechanics)
    assert mechanics["restoration_percentage"].value == 100
    assert mechanics["restoration_count_per_policy_period"].value == 1
    assert mechanics["same_hospitalization_use"].value is False
    assert mechanics["subsequent_hospitalization_use"].value is True
    assert mechanics["same_illness_use"].value is True
    assert mechanics["relapse_window_days"].value == 45
    assert mechanics["policy_year_reset"].value is True
    assert mechanics["carry_over_between_policy_years"].value is False


def test_ar30g0_quarantines_stale_transitional_coverage_audit() -> None:
    architecture = Path(
        "docs/architecture/AR_3_0_G0_STAR_COMPREHENSIVE_COMMERCIAL_PRESSURE_QUALIFICATION.md"
    ).read_text(encoding="utf-8")
    stale_audit = Path(
        "knowledge/health/coverage_audits/star_health_star_comprehensive_coverage_audit.json"
    ).read_text(encoding="utf-8")

    assert '"status": "INCOMPLETE"' in stale_audit
    assert "must not be used as a current governed coverage statement" in architecture
    assert "No AR-3.0 implementation may infer" in architecture
    assert "A new abstraction is permitted only if" in architecture
