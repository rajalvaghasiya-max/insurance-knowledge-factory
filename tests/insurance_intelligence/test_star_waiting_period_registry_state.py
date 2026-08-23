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
    assert any("30-day initial" in item and "certified" in item for item in lowered)
    assert any("ped" in item and "36 months" in item for item in lowered)
    assert any("buy-back" in item and "12 months" in item for item in lowered)
    assert any("specified-disease/procedure" in item and "24 months" in item for item in lowered)
    assert any("delivery" in item and "24 months" in item for item in lowered)
    assert any("bariatric" in item and "36 months" in item for item in lowered)
    assert any("preventive health check-up" in item and "30 days" in item for item in lowered)
    assert any("dental/ophthalmic" in item and "outside" in item for item in lowered)


def test_star_waiting_period_registry_references_concept_level_governed_closure() -> None:
    waiting = _waiting_period()
    expected = {
        "docs/architecture/STAR_COMPREHENSIVE_INITIAL_WAITING_PERIOD_MANUFACTURING_CLOSURE.md",
        "insurance_intelligence/rule_certification/star_health_initial_waiting_period.py",
        "docs/architecture/star_health_star_comprehensive_ped_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_ped_material_rules_spec.json",
        "docs/architecture/star_health_star_comprehensive_ped_buyback_multispan_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_specified_disease_waiting_period_multispan_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_delivery_new_born_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_bariatric_surgery_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_preventive_health_checkup_waiting_period_binding_spec.json",
        "docs/architecture/star_health_star_comprehensive_waiting_period_concept_certification_closure_2026-08-22.json",
    }
    assert expected <= set(waiting.evidence_reference_ids)
