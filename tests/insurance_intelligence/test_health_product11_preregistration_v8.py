import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs" / "architecture" / "health_post_hc1_neutral_cold_start_protocol_v8_product11.json"


def _load() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_product11_is_locked_before_any_gate_execution_or_selection() -> None:
    protocol = _load()
    experiment = protocol["experiment"]
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT11_GATE_A_EXECUTION"
    assert experiment["product_number"] == 11
    assert experiment["product_selected"] is False
    assert experiment["gate_a_started"] is False
    assert experiment["gate_b_started"] is False
    assert experiment["gate_c_started"] is False


def test_product11_keeps_semantic_baseline_and_uses_repaired_harness_baseline() -> None:
    protocol = _load()
    assert protocol["semantic_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert protocol["experiment_harness_baseline_commit"] == "784602b79d976873216f297ab296836e91cfa1ec"
    assert protocol["governance_freeze_commit"] == "7b5bb191f302cd46aeab188d6f5194bde06a7678"
    assert protocol["freeze"]["semantic_scoring_baseline_must_remain_f05ca07"] is True
    assert protocol["freeze"]["experiment_harness_baseline_must_remain_784602b7"] is True


def test_gate_a_freezes_exact_roots_and_transport_without_historical_reachability_reuse() -> None:
    protocol = _load()
    gate = protocol["gate_a_root_transport_fitness"]
    assert protocol["exact_preregistered_roots"] == [
        "https://irdai.gov.in/non-life-insurers1",
        "https://irdai.gov.in/health-insurers1",
        "https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount",
    ]
    assert gate["allowed_transport_sequence"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert gate["search_engine_fallback_allowed"] is False
    assert gate["ad_hoc_transport_allowed"] is False
    assert gate["historical_root_observations_are_not_current_proof"] is True


def test_gate_b_requires_source_specific_insurer_directory_authority_and_blind_projection() -> None:
    protocol = _load()
    gate = protocol["gate_b_blind_metadata_path_discovery"]
    assert gate["regulator_directory_classification_authority"] == "scripts.run_source_discovery.SourceDiscoveryRunner"
    assert gate["generic_discovery_regulatory_class_is_authoritative_for_regulator_directory"] is False
    assert gate["required_regulator_directory_page_type"] == "insurer_directory"
    assert "insurer_directory" in gate["authorized_metadata_page_types"]
    assert gate["raw_destination_url_may_cross_boundary"] is False
    assert gate["anchor_text_may_cross_boundary"] is False
    assert gate["body_text_may_cross_boundary"] is False
    assert gate["screenshot_may_cross_boundary"] is False
    assert gate["semantic_evidence_may_cross_boundary"] is False
    assert gate["product_detail_or_policy_wording_authorized"] is False


def test_product11_pool_is_deterministic_without_reopening_prior_experiments() -> None:
    protocol = _load()
    history = protocol["prior_experiment_eligibility"]
    gate = protocol["gate_c_neutral_selection"]
    expected = [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert history["eligible_insurers"] == expected
    assert gate["candidate_insurers"] == expected
    assert history["product8_contamination_quarantines_reopened"] is False
    assert history["product9_is_reopened_or_retried"] is False
    assert history["product10_is_reopened_or_retried"] is False
    assert gate["semantic_fit_may_affect_selection"] is False
    assert gate["selection_override_authorized"] is False


def test_post_selection_currentness_and_blindness_gates_remain_fail_closed() -> None:
    protocol = _load()
    post = protocol["post_selection_sequence"]
    metrics = protocol["primary_metrics"]
    assert post["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert post["post_selection_product_or_version_substitution_authorized"] is False
    assert post["semantic_pass_may_override_currentness_failure"] is False
    assert all(value == 0 for value in metrics.values())
    assert protocol["motor_readiness_gate"]["product11_unscored_cannot_satisfy_gate"] is True
