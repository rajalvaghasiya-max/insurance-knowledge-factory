from __future__ import annotations

import json
from pathlib import Path


PROTOCOL = Path("docs/architecture/health_post_hc1_neutral_cold_start_protocol_v10_product13.json")
FREEZE = Path("docs/architecture/health_product13_preregistration_v10_freeze.json")
AUTH = Path("docs/architecture/health_product13_gate_a_execution_authorization_v1.json")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product13_protocol_is_locked_before_gate_a() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["schema_version"] == "10.0"
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT13_GATE_A_EXECUTION"
    assert protocol["experiment"]["product_number"] == 13
    assert protocol["experiment"]["gate_a_started"] is False
    assert protocol["experiment"]["gate_b_started"] is False
    assert protocol["experiment"]["gate_c_started"] is False


def test_product13_pins_all_four_frozen_baselines() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["semantic_scoring_baseline_commit"].startswith("f05ca072")
    assert protocol["experiment_harness_baseline_commit"].startswith("784602b7")
    assert protocol["preselection_v2_freeze_commit"].startswith("97a12446")
    assert protocol["identity_currentness_acquisition_baseline_commit"] == (
        "74b5400fe9bb133870bc3f649b5749fe32200948"
    )


def test_product13_roots_and_transport_sequence_are_frozen() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["exact_preregistered_roots"] == [
        "https://irdai.gov.in/non-life-insurers1",
        "https://irdai.gov.in/health-insurers1",
        "https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount",
    ]
    gate_a = protocol["gate_a_root_transport_fitness"]
    assert gate_a["allowed_transport_sequence"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert gate_a["search_engine_fallback_allowed"] is False
    assert gate_a["ad_hoc_transport_allowed"] is False


def test_product13_requires_fresh_gate_a_and_gate_b() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["gate_a_root_transport_fitness"]["historical_product12_gate_a_pass_is_not_product13_proof"] is True
    assert protocol["gate_b_blind_metadata_path_discovery"]["historical_product12_gate_b_pass_is_not_product13_proof"] is True


def test_product13_candidate_pool_remains_conservative_and_unchanged() -> None:
    protocol = _load(PROTOCOL)
    expected = [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert protocol["prior_experiment_eligibility"]["eligible_insurers"] == expected
    assert protocol["gate_c_neutral_selection"]["candidate_insurers"] == expected
    assert protocol["prior_experiment_eligibility"]["product12_may_be_reopened_or_retried"] is False


def test_product13_gate_c_requires_new_identity_currentness_acquirer() -> None:
    protocol = _load(PROTOCOL)
    gate_c = protocol["gate_c_neutral_selection"]
    assert gate_c["governed_identity_currentness_acquisition_required_before_selection"] is True
    assert gate_c["identity_currentness_traversal_mode"] == (
        "bounded deterministic breadth-first machine-side traversal"
    )
    assert gate_c["only_authorized_metadata_artifact_classes_may_be_acquired"] is True
    assert gate_c["artifact_sha256_and_provenance_required"] is True
    assert gate_c["ambiguous_product_uin_version_or_currentness_fails_closed"] is True


def test_product13_selector_boundary_remains_raw_location_free() -> None:
    protocol = _load(PROTOCOL)
    gate_c = protocol["gate_c_neutral_selection"]
    assert gate_c["selector_product_metadata_input_contract"] == "blind_preselection_product_metadata_v2"
    assert gate_c["selector_currentness_input_contract"] == "blind_product_identity_currentness_evidence_v1"
    assert gate_c["selector_may_receive_raw_url_or_anchor_text"] is False
    assert gate_c["selector_may_receive_raw_parsed_file_path"] is False
    assert gate_c["selector_may_receive_raw_page_or_product_signal_output"] is False
    assert gate_c["selector_may_receive_semantic_bucket_presence_or_counts"] is False
    assert gate_c["selector_source_ref_may_be_used_as_authority_or_currentness_evidence"] is False


def test_product13_target_reads_remain_locked_until_positive_currentness() -> None:
    protocol = _load(PROTOCOL)
    assert protocol["post_selection_sequence"]["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert protocol["primary_metrics"]["preselection_target_clause_reads"] == 0
    assert protocol["primary_metrics"]["target_clause_reads_before_positive_currentness_eligibility"] == 0


def test_product13_runtime_and_selection_are_immutable_after_gate_start() -> None:
    protocol = _load(PROTOCOL)
    freeze = protocol["freeze"]
    assert freeze["runtime_change_allowed_during_initial_attempt"] is False
    assert freeze["identity_currentness_acquisition_runtime_change_allowed_after_gate_c_starts"] is False
    assert freeze["preselection_projection_change_allowed_after_gate_c_starts"] is False
    assert freeze["currentness_projection_change_allowed_after_gate_c_starts"] is False
    assert freeze["candidate_insurer_pool_change_allowed_after_gate_c_starts"] is False


def test_preregistration_freeze_preserves_history_and_zero_activity() -> None:
    freeze = _load(FREEZE)
    assert freeze["record_status"] == "FROZEN_PREREGISTRATION_PENDING_MERGE"
    assert freeze["preregistration_parent_commit"] == "74b5400fe9bb133870bc3f649b5749fe32200948"
    status = freeze["gate_status"]
    assert status["product_screening_started"] is False
    assert status["product_selected"] is False
    assert status["semantic_review_started"] is False
    assert status["target_clause_reads"] == 0
    history = freeze["historical_integrity"]
    assert history["product11_reopened_or_retried"] is False
    assert history["product12_reopened_or_retried"] is False
    assert history["product12_gate_results_may_substitute_for_product13"] is False
    assert history["motor_authorized"] is False


def test_preregistration_freeze_pins_raw_location_free_contracts() -> None:
    freeze = _load(FREEZE)
    boundary = freeze["selector_boundaries"]
    assert boundary["product_metadata_contract"] == "blind_preselection_product_metadata_v2"
    assert boundary["currentness_companion_contract"] == "blind_product_identity_currentness_evidence_v1"
    assert boundary["raw_url_allowed"] is False
    assert boundary["raw_anchor_allowed"] is False
    assert boundary["raw_parsed_path_allowed"] is False
    assert boundary["semantic_buckets_allowed"] is False
    assert boundary["source_ref_is_authority_or_currentness_evidence"] is False


def test_gate_a_authorization_authorizes_only_gate_a() -> None:
    auth = _load(AUTH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_PRODUCT13_PREREGISTRATION_MERGE"
    assert auth["gate_a_authorized"] is True
    assert auth["gate_b_authorized"] is False
    assert auth["gate_c_authorized"] is False
    assert auth["product_screening_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    assert auth["historical_product12_gate_a_result_may_substitute"] is False
