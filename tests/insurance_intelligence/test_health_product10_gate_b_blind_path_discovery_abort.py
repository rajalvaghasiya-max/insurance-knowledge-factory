import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ABORT = ROOT / "docs" / "architecture" / "health_product10_gate_b_blind_path_discovery_abort_2026-08-26.json"


def _load() -> dict:
    return json.loads(ABORT.read_text(encoding="utf-8"))


def test_product10_closes_unscored_at_gate_b_before_selection() -> None:
    record = _load()
    experiment = record["experiment"]
    decision = record["gate_decision"]
    assert experiment["gate_a_status"] == "PASS"
    assert experiment["gate_b_status"] == "FAIL"
    assert experiment["gate_c_started"] is False
    assert experiment["product_screening_started"] is False
    assert experiment["product_selected"] is False
    assert experiment["target_clause_reads"] == 0
    assert experiment["final_experiment_status"] == "EXPERIMENT_UNSCORED"
    assert decision["protocol_failure_outcome"] == "CLOSE_PRODUCT10_UNSCORED_BLIND_PATH_DISCOVERY_FAILURE"


def test_corrected_gate_b_execution_remained_blind_and_did_not_resolve_insurer_origins() -> None:
    record = _load()
    result = record["corrected_blind_execution_result"]
    metrics = record["blindness_and_method_metrics"]
    assert result["regulator_pages_captured_count"] == 30
    assert result["regulator_blind_projection_count"] == 7620
    assert result["resolved_candidate_count"] == 0
    assert result["unresolved_candidate_ids"] == ["chola", "magma", "navi", "shriram"]
    assert result["captured_insurer_origin_count"] == 0
    assert result["authorized_insurer_metadata_projection_count"] == 0
    assert result["raw_regulator_urls_emitted"] == 0
    assert result["raw_origin_urls_emitted"] == 0
    assert result["raw_discovered_urls_emitted"] == 0
    assert result["anchor_text_emitted"] == 0
    assert result["body_text_emitted"] == 0
    assert result["page_titles_emitted"] == 0
    assert result["screenshots_emitted"] == 0
    assert metrics["operator_raw_capture_reads"] == 0
    assert metrics["selector_raw_capture_reads"] == 0
    assert metrics["preselection_target_clause_reads"] == 0


def test_existing_source_specific_classifier_proves_directory_class_paths_exist() -> None:
    diagnostic = _load()["existing_capability_diagnostic"]
    assert diagnostic["source_specific_capability"] == "SourceDiscoveryRunner.classify_source_url"
    assert diagnostic["existing_precise_page_type"] == "insurer_directory"
    assert diagnostic["insurer_directory_links_classified_on_passing_roots"] == 36
    assert diagnostic["insurer_directory_links_per_passing_root"] == 18
    assert diagnostic["frozen_blind_projector_allowed_page_types_include_insurer_directory"] is False
    assert diagnostic["observed_contract_mismatch"] == (
        "EXISTING_SOURCE_SPECIFIC_INSURER_DIRECTORY_CLASS_NOT_AUTHORIZED_BY_FROZEN_BLIND_DISCOVERY_PROJECTION"
    )


def test_gate_b_failure_is_projection_contract_mismatch_not_transport_or_semantic_failure() -> None:
    record = _load()
    decision = record["gate_decision"]
    interpretation = record["methodology_interpretation"]
    assert decision["condition_satisfied"] is False
    assert decision["decision"] == "FAIL"
    assert decision["failure_reason"] == "FROZEN_BLIND_PROJECTION_CONTRACT_EXCLUDES_EXISTING_INSURER_DIRECTORY_CLASS"
    assert decision["gate_c_authorized"] is False
    assert decision["insurer_or_product_screening_authorized"] is False
    assert decision["mid_experiment_projector_extension_authorized"] is False
    assert interpretation["root_transport_failed"] is False
    assert interpretation["regulator_directory_paths_absent"] is False
    assert interpretation["semantic_repeatability_was_tested"] is False
    assert interpretation["semantic_repeatability_is_proven_or_disproven"] is False


def test_product10_cannot_be_repaired_by_extending_projector_mid_experiment() -> None:
    record = _load()
    decision = record["gate_decision"]
    interpretation = record["methodology_interpretation"]
    assert decision["alternate_post_result_resolution_method_authorized"] is False
    assert decision["mid_experiment_projector_extension_authorized"] is False
    assert interpretation["post_failure_method_repair_inside_product10_authorized"] is False
    assert interpretation["prospective_next_classification"] == (
        "REUSE_SOURCE_DISCOVERY_RUNNER_PLUS_SMALL_EXTEND_BLIND_PROJECTION_CONTRACT"
    )


def test_gate_b_execution_and_diagnostic_lineage_are_auditable_nonmerged_and_motor_stays_closed() -> None:
    record = _load()
    lineage = record["execution_lineage"]
    history = record["historical_integrity"]
    corrected = lineage["corrected_smoke"]
    diagnostic = lineage["source_classifier_diagnostic"]
    assert corrected["commit"] == "89bbc88e48f1839742a372f3c97141acbc2ffa42"
    assert corrected["workflow_run_id"] == 32939927843
    assert corrected["workflow_job_id"] == 98088633929
    assert corrected["factory_tests_after_smoke"] == 3054
    assert diagnostic["commit"] == "89941b776d5d0f1b6e46b67467b50969a4e1a362"
    assert diagnostic["workflow_run_id"] == 32940356432
    assert diagnostic["workflow_job_id"] == 98089899312
    assert diagnostic["total_insurer_directory_count"] == 36
    assert lineage["disposable_branches_may_merge"] is False
    assert history["product10_may_be_reopened_or_retried"] is False
    assert history["motor_authorized"] is False
