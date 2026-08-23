from insurance_intelligence.coverage_registry.contracts import ConceptCoverageStatus
from insurance_intelligence.coverage_registry.health_seed import STAR_COMPREHENSIVE_COVERAGE


def _waiting_period():
    return next(
        item for item in STAR_COMPREHENSIVE_COVERAGE.concepts
        if item.concept_id == "waiting_period"
    )


def test_star_waiting_period_is_certified_after_full_current_wording_audit() -> None:
    waiting = _waiting_period()

    assert waiting.status is ConceptCoverageStatus.CERTIFIED
    assert waiting.comparison_ready is False
    assert waiting.decision_support_ready is False
    lowered = tuple(item.lower() for item in waiting.limitations)
    assert any("standard 30-day initial wait" in item for item in lowered)
    assert any("standard 36-month ped" in item for item in lowered)
    assert any("optional ped buy-back to 12 months" in item for item in lowered)
    assert any("24-month specified-disease/procedure wait" in item for item in lowered)
    assert any("24-month delivery and new born wait" in item for item in lowered)
    assert any("36-month bariatric surgery wait" in item for item in lowered)
    assert any("30-day preventive health check-up wait" in item for item in lowered)
    assert any("dental/ophthalmic" in item and "classified separately" in item for item in lowered)


def test_star_waiting_period_registry_references_concept_level_governed_closure() -> None:
    waiting = _waiting_period()
    expected = {
        "docs/architecture/star_health_star_comprehensive_waiting_period_concept_pressure_inventory_2026-08-22.json",
        "docs/architecture/STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_MANUFACTURING_CLOSURE.md",
        "insurance_intelligence/rule_certification/star_health_initial_waiting_period.py",
        "docs/architecture/star_health_star_comprehensive_ped_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_ped_material_rules_spec.json",
        "docs/architecture/star_health_star_comprehensive_ped_buyback_multispan_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_specified_disease_waiting_period_multispan_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_specified_disease_material_rules_spec.json",
        "docs/architecture/star_health_star_comprehensive_delivery_newborn_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_delivery_newborn_material_rules_spec.json",
        "docs/architecture/star_health_star_comprehensive_bariatric_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_preventive_health_checkup_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_preventive_health_checkup_material_rules_spec.json",
        "docs/architecture/star_health_star_comprehensive_waiting_period_concept_certification_closure_2026-08-22.json",
    }
    assert expected <= set(waiting.evidence_reference_ids)
