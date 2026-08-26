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


def test_gate_b_used_passing_roots_but_resolved_no_preregistered_insurer_origin() -> None:
    record = _load()
    roots = record["passing_gate_a_roots_used"]
    resolution = record["blind_resolution_result"]
    assert len(roots) == 2
    assert all(item["accepted"] is True for item in roots)
    assert all(item["capture_strategy"] == "static_http" for item in roots)
    assert resolution["resolved_candidate_count"] == 0
    assert resolution["resolved_candidate_ids"] == []
    assert resolution["unresolved_candidate_ids"] == ["chola", "magma", "navi", "shriram"]


def test_gate_b_produced_no_authorized_projection_and_did_not_cross_blind_boundary() -> None:
    record = _load()
    projected = record["blind_projection_result"]
    metrics = record["blindness_and_method_metrics"]
    assert projected["captured_insurer_origin_count"] == 0
    assert projected["authorized_blind_projection_count"] == 0
    assert projected["passing_candidate_count"] == 0
    assert projected["raw_discovered_urls_emitted"] == 0
    assert projected["anchor_text_emitted"] == 0
    assert projected["body_text_emitted"] == 0
    assert projected["page_titles_emitted"] == 0
    assert projected["screenshots_emitted"] == 0
    assert metrics["operator_raw_capture_reads"] == 0
    assert metrics["selector_raw_capture_reads"] == 0
    assert metrics["raw_origin_urls_crossing_boundary"] == 0
    assert metrics["raw_discovered_urls_crossing_boundary"] == 0
    assert metrics["semantic_anchor_or_body_text_crossing_boundary"] == 0


def test_gate_b_failure_cannot_be_repaired_inside_product10() -> None:
    record = _load()
    decision = record["gate_decision"]
    interpretation = record["methodology_interpretation"]
    assert decision["condition_satisfied"] is False
    assert decision["decision"] == "FAIL"
    assert decision["gate_c_authorized"] is False
    assert decision["insurer_or_product_screening_authorized"] is False
    assert decision["alternate_post_result_resolution_method_authorized"] is False
    assert interpretation["post_failure_method_repair_inside_product10_authorized"] is False


def test_gate_b_failure_does_not_claim_semantic_repeatability_outcome() -> None:
    interpretation = _load()["methodology_interpretation"]
    assert interpretation["semantic_repeatability_was_tested"] is False
    assert interpretation["semantic_repeatability_is_proven_or_disproven"] is False
    assert interpretation["failure_scope"] == (
        "blind regulator-root to eligible-insurer-origin/path discovery under the locked v7 method"
    )


def test_gate_b_smoke_lineage_is_auditable_nonmerged_and_motor_stays_closed() -> None:
    record = _load()
    lineage = record["execution_lineage"]
    history = record["historical_integrity"]
    assert lineage["smoke_branch"] == "product10-gate-b-live-smoke"
    assert lineage["smoke_commit"] == "d3814624f757e727c13ec50da643b7d1bddae050"
    assert lineage["workflow_run_id"] == 32938825521
    assert lineage["workflow_job_id"] == 98085376730
    assert lineage["workflow_conclusion"] == "success"
    assert lineage["factory_tests_after_smoke"] == 3054
    assert lineage["smoke_branch_may_merge"] is False
    assert history["product10_may_be_reopened_or_retried"] is False
    assert history["motor_authorized"] is False
