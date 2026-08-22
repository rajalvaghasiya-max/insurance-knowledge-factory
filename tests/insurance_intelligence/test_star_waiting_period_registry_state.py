from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import STAR_COMPREHENSIVE_COVERAGE


def test_star_waiting_period_is_partial_after_initial_and_ped_certification() -> None:
    waiting = next(
        item for item in STAR_COMPREHENSIVE_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )

    assert waiting.status is ConceptCoverageStatus.PARTIAL
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    lowered = tuple(item.lower() for item in waiting.limitations)
    assert any("30-day initial" in item and "certified complete" in item for item in lowered)
    assert any("standard ped mechanic is certified" in item and "36 months" in item for item in lowered)
    assert any("buy-back" in item and "not certified" in item for item in lowered)
    assert any("specified-disease/procedure" in item and "remains outstanding" in item for item in lowered)
    assert any("overall waiting_period concept remains partial" in item for item in lowered)


def test_star_waiting_period_registry_references_governed_ped_slice() -> None:
    waiting = next(
        item for item in STAR_COMPREHENSIVE_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )
    expected = {
        "docs/architecture/STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_MANUFACTURING_CLOSURE.md",
        "insurance_intelligence/rule_certification/star_health_initial_waiting_period.py",
        "docs/architecture/star_health_star_comprehensive_ped_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_ped_material_rules_spec.json",
        "tests/insurance_intelligence/test_star_comprehensive_ped_waiting_period.py",
    }
    assert expected <= set(waiting.evidence_reference_ids)
