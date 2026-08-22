from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import BAJAJ_MY_HEALTH_CARE_V2_COVERAGE


def test_bajaj_waiting_period_stays_partial_after_initial_and_option_domain_certification() -> None:
    waiting = next(
        item for item in BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )
    assert waiting.status is ConceptCoverageStatus.PARTIAL
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    assert waiting.limitations
    lowered = tuple(item.lower() for item in waiting.limitations)
    assert any("initial waiting-period mechanic is certified complete" in item for item in lowered)
    assert any("ped and specified-disease/procedure" in item for item in lowered)
    assert any("option domains" in item and "certified complete" in item for item in lowered)
    assert any("no customer-specific duration is selected" in item for item in lowered)
    assert any("maternity and baby-care" in item for item in lowered)
    assert any("overall waiting_period concept remains partial" in item for item in lowered)


def test_bajaj_waiting_period_registry_references_option_domain_closure() -> None:
    waiting = next(
        item for item in BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )
    assert "docs/architecture/bajaj_my_health_care_v2_ped_waiting_period_option_domain_binding_spec.json" in waiting.evidence_reference_ids
    assert "docs/architecture/bajaj_my_health_care_v2_specific_disease_waiting_period_option_domain_binding_spec.json" in waiting.evidence_reference_ids
    assert "docs/architecture/bajaj_my_health_care_v2_waiting_period_option_domain_certification_closure_2026-08-22.json" in waiting.evidence_reference_ids


def test_bajaj_copayment_certification_is_unchanged() -> None:
    copayment = next(
        item for item in BAJAJ_MY_HEALTH_CARE_V2_COVERAGE.concepts
        if item.concept_id == "copayment"
    )
    assert copayment.status is ConceptCoverageStatus.CERTIFIED
    assert copayment.comparison_ready is False
    assert copayment.decision_support_ready is False
