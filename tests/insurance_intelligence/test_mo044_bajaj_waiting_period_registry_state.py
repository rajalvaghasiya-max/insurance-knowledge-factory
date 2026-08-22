from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import BAJAJ_MY_HEALTH_CARE_V2_COVERAGE


def test_bajaj_waiting_period_enters_registry_as_partial_not_certified() -> None:
    waiting = next(
        item for item in BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )
    assert waiting.status is ConceptCoverageStatus.PARTIAL
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert waiting.limitations
    assert any("enhanced-Sum-Insured" in item for item in waiting.limitations)
    assert any("PED" in item for item in waiting.limitations)


def test_bajaj_copayment_certification_is_unchanged() -> None:
    copayment = next(
        item for item in BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.concepts
        if item.concept_id == "copayment"
    )
    assert copayment.status is ConceptCoverageStatus.CERTIFIED
    assert copayment.comparison_ready is False
    assert copayment.decision_support_ready is False
