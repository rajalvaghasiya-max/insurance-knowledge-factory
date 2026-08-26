import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs" / "architecture" / "health_post_hc1_neutral_cold_start_protocol_v7_product10.json"


def _load() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_product10_is_locked_before_any_gate_or_selection() -> None:
    protocol = _load()
    experiment = protocol["experiment"]

    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT10_GATE_A_EXECUTION"
    assert experiment["product_number"] == 10
    assert experiment["product_selected"] is False
    assert experiment["gate_a_started"] is False
    assert experiment["gate_b_started"] is False
    assert experiment["gate_c_started"] is False


def test_gate_a_reuses_exact_frozen_transport_sequence_and_no_search_fallback() -> None:
    protocol = _load()
    gate = protocol["gate_a_root_transport_fitness"]

    assert protocol["root_transport_fitness_contract_path"] == (
        "docs/architecture/health_root_transport_fitness_gate_v1.json"
    )
    assert gate["allowed_transport_sequence"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert gate["authoritative_implementation"] == "collectors.capture_engine.CaptureEngine"
    assert gate["browser_transport_is_explicitly_preregistered"] is True
    assert gate["search_engine_fallback_allowed"] is False
    assert gate["ad_hoc_transport_allowed"] is False


def test_gate_b_blindness_blocks_raw_url_and_semantic_content() -> None:
    protocol = _load()
    gate = protocol["gate_b_blind_metadata_path_discovery"]

    assert gate["machine_may_capture_raw_regulator_or_insurer_page_content"] is True
    assert gate["machine_may_parse_raw_html_anchor_text_and_destination_urls"] is True
    assert gate["operator_may_view_raw_machine_capture"] is False
    assert gate["selector_may_view_raw_machine_capture"] is False
    assert gate["operator_or_selector_allowed_contract"] == "blind_discovery_link_metadata_v1"
    assert gate["raw_destination_url_may_cross_boundary"] is False
    assert gate["raw_url_path_may_cross_boundary"] is False
    assert gate["anchor_text_may_cross_boundary"] is False
    assert gate["page_title_may_cross_boundary"] is False
    assert gate["body_text_may_cross_boundary"] is False
    assert gate["screenshot_may_cross_boundary"] is False
    assert gate["semantic_evidence_may_cross_boundary"] is False


def test_product10_pool_is_conservative_and_product9_is_not_reopened() -> None:
    protocol = _load()
    prior = protocol["prior_experiment_eligibility"]
    gate_c = protocol["gate_c_neutral_selection"]

    expected = [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert prior["eligible_insurers"] == expected
    assert gate_c["candidate_insurers"] == expected
    assert prior["product8_contamination_quarantines_reopened"] is False
    assert prior["product8_contaminated_insurers_eligible"] is False
    assert prior["product9_is_reopened_or_retried"] is False
    assert prior["future_exact_product_prior_exposure_audit_required_after_selection"] is True


def test_gate_c_is_downstream_of_root_and_blind_path_fitness() -> None:
    protocol = _load()
    gate_c = protocol["gate_c_neutral_selection"]
    post = protocol["post_selection_sequence"]

    assert gate_c["begins_only_after_gate_a_and_gate_b_pass"] is True
    assert gate_c["selector_discovery_input_contract"] == "blind_discovery_link_metadata_v1"
    assert gate_c["selector_product_metadata_input_contract"] == "blind_preselection_product_metadata_v1"
    assert gate_c["selector_may_receive_raw_url_or_anchor_text"] is False
    assert gate_c["selector_may_receive_raw_page_or_product_signal_output"] is False
    assert gate_c["selector_may_receive_semantic_bucket_presence_or_counts"] is False
    assert gate_c["semantic_fit_may_affect_selection"] is False
    assert gate_c["selection_override_authorized"] is False
    assert post["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert post["post_selection_product_or_version_substitution_authorized"] is False


def test_frozen_baselines_metrics_and_motor_gate_remain_fail_closed() -> None:
    protocol = _load()

    assert protocol["semantic_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert protocol["experiment_harness_baseline_commit"] == "edf344b34196258b04041f2fda2caa07d06d1f72"
    assert protocol["governance_freeze_commit"] == "6051d6b3c8c9c4d203f2f1a532db63e6081897dc"
    assert all(value == 0 for value in protocol["primary_metrics"].values())
    motor = protocol["motor_readiness_gate"]
    assert motor["product9_unscored_cannot_satisfy_gate"] is True
    assert motor["product10_unscored_cannot_satisfy_gate"] is True
