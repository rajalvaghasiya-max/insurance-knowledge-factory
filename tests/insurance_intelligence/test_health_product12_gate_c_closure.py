from __future__ import annotations

import json
from pathlib import Path


GATE_C_PATH = Path(
    "docs/architecture/health_product12_gate_c_no_eligible_blind_selection_2026-08-26.json"
)
NEXT_AUTH_PATH = Path(
    "docs/architecture/health_product12_closure_and_next_authorization_v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product12_gate_c_freezes_authoritative_no_selection_evidence() -> None:
    record = _load(GATE_C_PATH)
    assert record["record_status"] == "FROZEN_GATE_C_NO_ELIGIBLE_BLIND_SELECTION"
    assert record["preregistration"]["gate_b_freeze_merge_commit"] == (
        "f5969c8f201d309d9b655ae8b155c61f7f8be51a"
    )
    assert record["execution_evidence"]["disposable_commit"] == (
        "aa2223d60b59bfaabb079e89ff5dffd3a45c3096"
    )
    assert record["execution_evidence"]["workflow_run_id"] == 32949586622
    assert record["execution_evidence"]["workflow_job_id"] == 98117757398
    assert record["execution_evidence"]["full_suite_result"] == "3117 passed in 8.81s"


def test_product12_gate_c_uses_v2_and_has_no_eligible_exact_uin() -> None:
    record = _load(GATE_C_PATH)
    assert record["preregistration"]["selector_product_metadata_contract"] == (
        "blind_preselection_product_metadata_v2"
    )
    ledger = {item["candidate_id"]: item for item in record["screening_ledger"]}
    assert ledger["shriram"]["blind_destination_count"] == 7
    assert ledger["shriram"]["v2_projection_count"] == 7
    assert ledger["shriram"]["exact_uin_count"] == 0
    assert ledger["shriram"]["eligible_count"] == 0
    assert record["selection_decision"]["decision"] == "NO_ELIGIBLE_BLIND_SELECTION"
    assert record["selection_decision"]["selected_product"] is None


def test_product12_gate_c_preserves_blindness_and_zero_semantic_activity() -> None:
    record = _load(GATE_C_PATH)
    metrics = record["blindness_metrics"]
    for key in (
        "selector_raw_url_reads",
        "selector_raw_anchor_reads",
        "selector_raw_parsed_file_path_reads",
        "selector_raw_page_or_product_signal_reads",
        "selector_semantic_bucket_reads",
        "raw_urls_emitted",
        "raw_paths_emitted",
        "anchor_text_emitted",
        "body_text_emitted",
        "screenshots_emitted",
    ):
        assert metrics[key] == 0
    assert metrics["semantic_fit_used"] is False
    guard = record["post_selection_guard"]
    assert guard["product_document_acquisition_started"] is False
    assert guard["semantic_review_started"] is False
    assert guard["target_clause_reads"] == 0


def test_product12_closes_unscored_without_semantic_inference_or_retry() -> None:
    record = _load(GATE_C_PATH)
    outcome = record["outcome"]
    assert outcome["classification"] == "EXPERIMENT_UNSCORED"
    assert outcome["closure_reason"] == (
        "CLOSE_PRODUCT12_UNSCORED_NO_ELIGIBLE_BLIND_SELECTION"
    )
    assert outcome["copayment_classification"] is None
    assert outcome["waiting_period_classification"] is None
    assert outcome["repeatability_verdict"] == "NOT_EVALUATED"
    assert outcome["motor_readiness_satisfied"] is False
    integrity = record["historical_integrity"]
    assert integrity["product12_may_be_retried_under_protocol_v9"] is False
    assert integrity["product12_semantic_result_may_be_inferred"] is False


def test_next_authorization_is_fitness_review_only() -> None:
    auth = _load(NEXT_AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_PRODUCT12_CLOSURE_MERGE"
    assert auth["product13_preregistration_authorized"] is False
    assert auth["motor_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    assert auth["authorized_next_action"] == (
        "HEALTH_PRESELECTION_CURRENTNESS_PATH_FITNESS_REVIEW_ONLY"
    )
    scope = auth["review_scope"]
    assert scope["may_compare_product11_and_product12_preselection_failures"] is True
    assert scope["may_retry_product12"] is False
    assert scope["may_read_target_clauses"] is False
    assert scope["may_loosen_v2_raw_location_firewall"] is False
