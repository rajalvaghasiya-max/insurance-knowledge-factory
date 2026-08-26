from __future__ import annotations

import json
from pathlib import Path


PROTOCOL_PATH = Path(
    "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v9_product12.json"
)


def _protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_product12_is_new_locked_experiment_on_v2_baseline() -> None:
    protocol = _protocol()
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT12_GATE_A_EXECUTION"
    assert protocol["experiment"]["product_number"] == 12
    assert protocol["experiment"]["gate_a_started"] is False
    assert protocol["experiment"]["gate_b_started"] is False
    assert protocol["experiment"]["gate_c_started"] is False
    assert protocol["preselection_v2_freeze_commit"] == (
        "97a12446c389d3f872bbbc02a1e25024d870980a"
    )
    assert protocol["blind_preselection_projection_implementation"].endswith(
        "BlindPreselectionMetadataProjectorV2"
    )


def test_product12_reruns_gate_a_and_gate_b_instead_of_inheriting_product11_passes() -> None:
    protocol = _protocol()
    gate_a = protocol["gate_a_root_transport_fitness"]
    gate_b = protocol["gate_b_blind_metadata_path_discovery"]
    assert gate_a["historical_product11_gate_a_pass_is_not_current_product12_proof"] is True
    assert gate_b["historical_product11_gate_b_pass_is_not_current_product12_proof"] is True
    assert gate_a["must_complete_before_gate_b"] is True
    assert gate_b["must_complete_before_gate_c"] is True


def test_product12_preserves_exact_roots_and_clean_insurer_pool() -> None:
    protocol = _protocol()
    assert protocol["exact_preregistered_roots"] == [
        "https://irdai.gov.in/non-life-insurers1",
        "https://irdai.gov.in/health-insurers1",
        "https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount",
    ]
    expected = [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert protocol["prior_experiment_eligibility"]["eligible_insurers"] == expected
    assert protocol["gate_c_neutral_selection"]["candidate_insurers"] == expected
    assert protocol["prior_experiment_eligibility"]["product11_may_be_reopened_or_retried"] is False


def test_product12_gate_c_names_v2_and_forbids_raw_selector_inputs() -> None:
    gate_c = _protocol()["gate_c_neutral_selection"]
    assert gate_c["selector_product_metadata_input_contract"] == (
        "blind_preselection_product_metadata_v2"
    )
    assert gate_c["selector_may_receive_raw_url_or_anchor_text"] is False
    assert gate_c["selector_may_receive_raw_parsed_file_path"] is False
    assert gate_c["selector_may_receive_raw_page_or_product_signal_output"] is False
    assert gate_c["selector_may_receive_semantic_bucket_presence_or_counts"] is False
    assert gate_c["selector_boundary_must_reject_raw_url_payloads"] is True
    assert gate_c["selector_boundary_must_reject_raw_anchor_payloads"] is True


def test_product12_source_ref_is_distinctness_only_not_authority_or_currentness() -> None:
    gate_c = _protocol()["gate_c_neutral_selection"]
    assert gate_c["selector_source_ref_may_be_used_as_authority_or_currentness_evidence"] is False
    assert "Opaque source_ref proves only source distinctness" in gate_c["currentness_corroboration"]


def test_product12_preserves_zero_target_reads_and_no_substitution() -> None:
    protocol = _protocol()
    post = protocol["post_selection_sequence"]
    metrics = protocol["primary_metrics"]
    assert post["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert post["post_selection_product_or_version_substitution_authorized"] is False
    assert metrics["selector_raw_url_reads"] == 0
    assert metrics["selector_raw_anchor_reads"] == 0
    assert metrics["selector_raw_parsed_file_path_reads"] == 0
    assert metrics["preselection_target_clause_reads"] == 0
    assert metrics["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert metrics["post_selection_product_or_version_substitutions"] == 0
    assert metrics["selection_rule_overrides"] == 0


def test_product12_lock_forbids_runtime_or_projection_repair_mid_attempt() -> None:
    freeze = _protocol()["freeze"]
    assert freeze["runtime_change_allowed_during_initial_attempt"] is False
    assert freeze["root_list_change_allowed_after_gate_a_starts"] is False
    assert freeze["blind_discovery_projection_change_allowed_after_gate_b_starts"] is False
    assert freeze["preselection_projection_change_allowed_after_gate_c_starts"] is False
    assert freeze["candidate_insurer_pool_change_allowed_after_gate_c_starts"] is False
    assert freeze["preselection_v2_baseline_must_remain_97a12446"] is True


def test_motor_remains_closed_before_product12_repeatability_result() -> None:
    motor = _protocol()["motor_readiness_gate"]
    assert motor["authorized_outcomes"] == [
        "STRONG_REPEATABILITY_PROVEN",
        "MINIMUM_REPEATABILITY_PROVEN",
    ]
    assert motor["product11_unscored_cannot_satisfy_gate"] is True
    assert motor["product12_not_yet_executed_cannot_satisfy_gate"] is True
