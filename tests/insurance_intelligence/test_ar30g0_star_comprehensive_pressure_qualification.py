from pathlib import Path

from insurance_intelligence.benefits.contracts import PublicationStatus, ReviewStatus
from insurance_intelligence.benefits.star_comprehensive import (
    STAR_COMPREHENSIVE_RESTORATION_IMPLEMENTATION,
)
from insurance_intelligence.rule_certification.star_health import (
    STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID,
    STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH,
    run_star_comprehensive_conditional_copayment_certification,
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
    result = run_star_comprehensive_conditional_copayment_certification()

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()
    assert {check.component_id: check.actual_status for check in result.component_checks} == {
        "obligation_value": "SATISFIED",
        "trigger_condition": "SATISFIED",
        "applicability_scope": "SATISFIED",
        "exception_condition": "SATISFIED",
        "calculation_basis": "SATISFIED",
    }

    # G0 qualifies the current rule-certification anchor, which is bound to
    # retained governed evidence. It deliberately does not require historical
    # migration/publication runtime outputs to be materialized in the checkout.
    assert STAR_COMPREHENSIVE_COPAYMENT_BINDING_PATH == (
        "knowledge/factory/registry_backed/star_health_star_comprehensive/"
        "generic_legal_condition_binding/"
        "star_health_star_comprehensive_conditional_copayment.json"
    )
    assert STAR_COMPREHENSIVE_COPAYMENT_ASSERTION_ID == (
        "ga_star_comprehensive_entry_age_61_conditional_copayment_v1"
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
