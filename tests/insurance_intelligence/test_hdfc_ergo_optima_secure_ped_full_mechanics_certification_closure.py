from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSURE = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_v8_ped_full_mechanics_certification_closure_2026-08-22.json"
)


def _closure() -> dict:
    return json.loads(CLOSURE.read_text(encoding="utf-8"))


def test_hdfc_ped_full_mechanics_certification_closed_pass_complete() -> None:
    closure = _closure()
    result = closure["certification_result"]

    assert result["outcome"] == "PASS"
    assert result["completeness"] == "COMPLETE"
    assert result["explanation_permitted"] is True
    assert result["failures"] == []
    assert set(result["satisfied_components"]) == {
        "duration_option_domain",
        "waiting_period_subject",
        "selection_basis",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "sum_insured_enhancement_effect",
        "post_wait_condition",
    }


def test_hdfc_ped_full_mechanics_preserves_exact_multispan_attribution() -> None:
    attribution = _closure()["evidence_attribution"]

    assert attribution["duration_option_domain"] == ["candidate_page_26"]
    assert attribution["waiting_period_subject"] == ["candidate_page_30"]
    assert attribution["selection_basis"] == ["candidate_page_30", "candidate_page_26"]
    assert attribution["start_basis"] == ["candidate_page_30"]
    assert attribution["applicability_scope"] == ["candidate_page_30"]
    assert attribution["continuity_or_credit_rule"] == ["candidate_page_31"]
    assert attribution["sum_insured_enhancement_effect"] == ["candidate_page_31"]
    assert attribution["post_wait_condition"] == ["candidate_page_31"]


def test_hdfc_ped_full_mechanics_keeps_schedule_selected_duration_unresolved() -> None:
    mechanic = _closure()["mechanic"]
    governance = _closure()["governance"]

    assert mechanic["duration_options"] == [
        {"duration_value": 12, "duration_unit": "MONTHS"},
        {"duration_value": 24, "duration_unit": "MONTHS"},
        {"duration_value": 36, "duration_unit": "MONTHS"},
    ]
    assert mechanic["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert mechanic["policy_instance_resolution_status"] == "not_resolved_without_schedule_selection"
    assert governance["policy_instance_duration_without_schedule_authorized"] is False


def test_hdfc_waiting_period_concept_is_not_prematurely_promoted() -> None:
    governance = _closure()["governance"]
    gate = _closure()["next_gate"]

    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["full_waiting_period_concept_certified"] is False
    assert gate["gate_id"] == "BIND_AND_CERTIFY_HDFC_SPECIFIED_DISEASE_PROCEDURE_WAITING_PERIOD"
    assert gate["runtime_change_authorized"] is False


def test_hdfc_multispan_generalization_remains_generic() -> None:
    result = _closure()["generalization_result"]

    assert result["third_product_pressure_exposed_generic_gap"] is True
    assert result["generic_multispan_binding_added"] is True
    assert result["generic_multispan_certification_added"] is True
    assert result["insurer_specific_runtime_code_added"] is False
    assert result["result"] == "PASS"
