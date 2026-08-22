from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROOF = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_v8_initial_waiting_period_cold_start_proof_2026-08-22.json"
)


def _proof() -> dict:
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_hdfc_initial_wait_live_binding_is_recorded_exactly() -> None:
    proof = _proof()
    binding = proof["binding"]

    assert proof["product"]["uin"] == "HDFHLIP26058V082526"
    assert binding["live_execution_status"] == "PASS"
    assert binding["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert binding["resolution_status"] == "resolved_from_mechanism_evidence"
    assert binding["waiting_period_type"] == "INITIAL"
    assert binding["duration_value"] == 30
    assert binding["duration_unit"] == "DAYS"
    assert binding["value_source"] == "PRODUCT_FIXED"
    assert binding["candidate_id"] == "candidate_page_32"
    assert binding["source_page"] == 32
    assert binding["candidate_text_sha256"] == (
        "c3a9935698e24f4411d12a47bdcc1e3b22573ccca1b84adb6faa4cf647737c42"
    )


def test_hdfc_semantic_cold_start_used_zero_new_runtime_python() -> None:
    measurement = _proof()["generalization_measurement"]

    assert measurement["new_runtime_python_changes_for_registration"] == 0
    assert measurement["new_runtime_python_changes_for_binding"] == 0
    assert measurement["insurer_specific_runtime_code"] is False
    assert measurement["result"] == "SEMANTIC_COLD_START_PASS"
    assert "WaitingPeriodBinding" in measurement["generic_runtime_reused"]


def test_hdfc_initial_wait_certification_must_reuse_generic_certifier() -> None:
    gate = _proof()["certification_gate"]

    assert gate["existing_generic_certifier"] == (
        "insurance_intelligence.rule_certification.waiting_period"
    )
    assert gate["new_runtime_python_authorized"] is False
    assert gate["expected_outcome"] == "PASS"
    assert gate["expected_completeness"] == "COMPLETE"
    assert gate["expected_explanation_permitted"] is True
    assert set(gate["expected_components"]) == {
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "exception_condition",
    }


def test_hdfc_initial_wait_proof_does_not_authorize_downstream_promotion() -> None:
    governance = _proof()["governance"]

    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert governance["customer_specific_eligibility_authorized"] is False


def test_next_pressure_is_hdfc_ped_option_architecture() -> None:
    pressure = _proof()["next_pressure"]

    assert pressure["concept"] == "PRE_EXISTING_DISEASE"
    assert "36-month" in pressure["reason"]
    assert "24-month" in pressure["reason"]
    assert "12-month" in pressure["reason"]
    assert "option-domain" in pressure["reason"]
