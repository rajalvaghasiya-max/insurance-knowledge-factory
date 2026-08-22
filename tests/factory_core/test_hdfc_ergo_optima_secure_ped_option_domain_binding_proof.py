from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROOF = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_v8_ped_option_domain_binding_proof_2026-08-22.json"
)


def _proof() -> dict:
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_hdfc_ped_option_domain_live_binding_passed_without_runtime_changes() -> None:
    proof = _proof()
    binding = proof["binding"]
    generalization = proof["generalization_result"]

    assert binding["binding_status"] == "reviewed_waiting_period_option_domain_bound_not_published"
    assert binding["resolution_status"] == "unresolved_schedule_option_domain"
    assert binding["publication_status"] == "bound_not_published"
    assert binding["policy_instance_resolution_status"] == "not_resolved_without_schedule_selection"
    assert generalization["generic_option_domain_runtime_reused"] is True
    assert generalization["runtime_python_changes"] == 0
    assert generalization["insurer_specific_runtime_code"] is False
    assert generalization["result"] == "PASS"


def test_hdfc_ped_option_domain_preserves_all_authoritative_duration_options() -> None:
    binding = _proof()["binding"]

    assert binding["waiting_period_type"] == "PRE_EXISTING_DISEASE"
    assert binding["options"] == [
        {"duration_value": 12, "duration_unit": "MONTHS"},
        {"duration_value": 24, "duration_unit": "MONTHS"},
        {"duration_value": 36, "duration_unit": "MONTHS"},
    ]
    assert binding["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert binding["scope_type"] == "POLICY_WIDE"
    assert binding["selected_duration_present"] is False


def test_hdfc_ped_option_domain_remains_bound_to_exact_reviewed_candidates() -> None:
    evidence = _proof()["evidence"]

    assert evidence == [
        {
            "role": "mechanism",
            "candidate_id": "candidate_page_30",
            "source_page": 30,
            "candidate_text_sha256": "fceba7174d309103ee95afd6ba031c8109a45d0d97ac0373381a737bb766963e",
        },
        {
            "role": "option_domain",
            "candidate_id": "candidate_page_26",
            "source_page": 26,
            "candidate_text_sha256": "05864e66649d506387902d20f252bb8df552372b77a2b10e09d5e10ea1557dd2",
        },
    ]


def test_hdfc_ped_duration_domain_proof_does_not_overclaim_full_ped_mechanics() -> None:
    proof = _proof()
    governance = proof["governance"]
    deferred = proof["deferred_full_ped_mechanics"]

    assert governance["policy_schedule_required_for_selected_duration"] is True
    assert governance["full_ped_mechanics_certified"] is False
    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False
    assert governance["comparison_ready_authorized"] is False
    assert governance["decision_support_ready_authorized"] is False
    assert deferred["source_page"] == 31
    assert set(deferred["pending_semantics"]) == {
        "continuity_or_portability_credit",
        "sum_insured_enhancement_reapplication_completion",
        "post_wait_declaration_and_insurer_acceptance_condition",
    }


def test_next_gate_is_generic_ped_option_domain_certification() -> None:
    gate = _proof()["next_gate"]

    assert gate["gate_id"] == "CERTIFY_HDFC_PED_DURATION_OPTION_DOMAIN"
    assert "existing generic waiting-period option-domain certifier" in gate["success_condition"]
    assert "without selecting a policy-instance duration" in gate["success_condition"]
