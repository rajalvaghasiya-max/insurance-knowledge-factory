from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_waiting_period_pressure_inventory_2026-08-22.json"
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def _load() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_inventory_is_bound_to_current_v2_not_historical_v1() -> None:
    inventory = _load()
    assert inventory["product_identity"]["uin"] == "BAJHLIP26074V022526"
    assert inventory["source"]["document_id"] == "bajaj_my_health_care_policy_wording_v2"
    assert inventory["source"]["content_sha256"] == CURRENT_SHA
    assert inventory["source"]["temporal_status_required"] == "current_observed_reviewed"
    assert inventory["governance_decision"]["historical_v1_inventory_authoritative"] is False


def test_five_material_waiting_period_pressure_cases_are_kept_distinct() -> None:
    cases = _load()["pressure_cases"]
    assert len(cases) == 5
    assert {item["waiting_period_type"] for item in cases} == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "INITIAL",
        "MATERNITY",
        "BABY_CARE",
    }


def test_schedule_selected_waits_are_not_forced_into_scalar_mechanic() -> None:
    by_type = {item["waiting_period_type"]: item for item in _load()["pressure_cases"]}
    for waiting_period_type in (
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "MATERNITY",
        "BABY_CARE",
    ):
        item = by_type[waiting_period_type]
        assert item["schedule_dependency"] is True
        assert item["resolved_mechanic_representable"] is False

    assert by_type["PRE_EXISTING_DISEASE"]["selection_domain"] == [
        {"value": 1, "unit": "YEARS"},
        {"value": 2, "unit": "YEARS"},
        {"value": 3, "unit": "YEARS"},
    ]
    assert by_type["SPECIFIC_DISEASE_PROCEDURE"]["selection_domain"] == [
        {"value": 1, "unit": "YEARS"},
        {"value": 2, "unit": "YEARS"},
        {"value": 3, "unit": "YEARS"},
    ]


def test_initial_wait_is_the_only_safe_immediate_scalar_manufacturing_target() -> None:
    inventory = _load()
    initial = next(
        item for item in inventory["pressure_cases"] if item["waiting_period_type"] == "INITIAL"
    )
    assert initial["base_plan_value"] == {"value": 30, "unit": "DAYS"}
    assert initial["schedule_dependency"] is False
    assert initial["accident_exception"] is True
    assert initial["continuous_coverage_waiver_after_months"] == 12
    assert initial["sum_insured_enhancement_reapplication"] is True
    assert initial["resolved_mechanic_representable"] is True
    assert inventory["governance_decision"]["safe_immediate_manufacturing_target"] == "bajaj_v2_initial_wait"


def test_inventory_does_not_authorize_wholesale_mo028b_recovery() -> None:
    decision = _load()["governance_decision"]
    assert decision["scalar_contract_fit"] == "PARTIAL"
    assert decision["schedule_selected_option_domain_requires_separate_representation"] is True
    assert decision["recover_full_generic_knowledge_stack"] == "PROHIBITED_WITHOUT_ADDITIONAL_PRESSURE"
    assert decision["architecture_change"] == "TARGETED_REPRESENTATIONAL_PRESSURE_ONLY"
