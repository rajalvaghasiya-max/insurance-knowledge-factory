from pathlib import Path

from insurance_intelligence.coverage_registry.contracts import (
    ConceptCoverageStatus,
    ProductLifecycleStatus,
)
from insurance_intelligence.coverage_registry.health_seed import (
    BAJAJ_MY_HEALTH_CARE_V2_COVERAGE,
    HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE,
    HEALTH_COVERAGE_REGISTRY,
    STAR_COMPREHENSIVE_COVERAGE,
)
from insurance_intelligence.coverage_registry.reporting import build_coverage_review_report


ROOT = Path(__file__).resolve().parents[2]


def _concept(product, concept_id):
    return next(item for item in product.concepts if item.concept_id == concept_id)


def _copayment(product):
    return _concept(product, "copayment")


def test_seed_contains_current_governed_health_pilot_products() -> None:
    assert {item.product_reference for item in HEALTH_COVERAGE_REGISTRY.products} == {
        "star_health:star_comprehensive:SHAHLIP26044V092526",
        "bajaj_allianz_general:my_health_care:BAJHLIP26074V022526",
        "hdfc_ergo:optima_secure:HDFHLIP26058V082526",
    }


def test_star_and_bajaj_copayment_are_certified_but_not_promoted_to_downstream_readiness() -> None:
    for product in (STAR_COMPREHENSIVE_COVERAGE, BAJAJ_MY_HEALTH_CARE_V2_COVERAGE):
        copayment = _copayment(product)
        assert copayment.status is ConceptCoverageStatus.CERTIFIED
        assert copayment.comparison_ready is False
        assert copayment.decision_support_ready is False
        assert product.comparison_ready_concept_ids == ()
        assert product.decision_support_ready_concept_ids == ()


def test_star_waiting_period_is_certified_without_downstream_readiness() -> None:
    waiting = _concept(STAR_COMPREHENSIVE_COVERAGE, "waiting_period")
    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert STAR_COMPREHENSIVE_COVERAGE.comparison_ready_concept_ids == ()
    assert STAR_COMPREHENSIVE_COVERAGE.decision_support_ready_concept_ids == ()


def test_hdfc_waiting_period_is_certified_without_downstream_readiness() -> None:
    waiting = _concept(HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE, "waiting_period")
    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.comparison_ready_concept_ids == ()
    assert HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.decision_support_ready_concept_ids == ()


def test_seed_does_not_infer_product_lifecycle_from_current_document_evidence() -> None:
    for product in HEALTH_COVERAGE_REGISTRY.products:
        assert product.lifecycle_status is ProductLifecycleStatus.STATUS_UNKNOWN
        assert product.status_evidence_reference_ids == ()
        assert product.status_last_verified_at is None


def test_every_seed_evidence_reference_exists_in_current_repository() -> None:
    for product in HEALTH_COVERAGE_REGISTRY.products:
        for concept in product.concepts:
            for reference in concept.evidence_reference_ids:
                assert (ROOT / reference).is_file(), reference


def test_report_exposes_certification_without_claiming_comparison_or_decision_readiness() -> None:
    report = build_coverage_review_report(HEALTH_COVERAGE_REGISTRY)
    assert len(report.product_summaries) == 3
    by_product = {item.product_reference: item for item in report.product_summaries}
    assert by_product[STAR_COMPREHENSIVE_COVERAGE.product_reference].certified_concept_count == 2
    assert by_product[BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.product_reference].certified_concept_count == 2
    assert by_product[HDFC_ERGO_OPTIMA_SECURE_V8_COVERAGE.product_reference].certified_concept_count == 1
    assert all(item.comparison_ready_concept_count == 0 for item in report.product_summaries)
    assert all(item.decision_support_ready_concept_count == 0 for item in report.product_summaries)
    assert sum(1 for gap in report.gaps if gap.gap_type == "LIFECYCLE_STATUS_UNKNOWN") == 3


def test_historical_activ_one_snapshot_is_not_reintroduced_as_current_seed_truth() -> None:
    assert "aditya_birla_health" not in HEALTH_COVERAGE_REGISTRY.insurer_ids
