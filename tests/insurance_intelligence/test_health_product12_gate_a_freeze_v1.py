from __future__ import annotations

import json
from pathlib import Path


GATE_A_PATH = Path(
    "docs/architecture/health_product12_gate_a_root_transport_fitness_2026-08-26.json"
)
GATE_B_AUTH_PATH = Path(
    "docs/architecture/health_product12_gate_b_execution_authorization_v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product12_gate_a_freezes_fresh_pass_evidence() -> None:
    record = _load(GATE_A_PATH)
    assert record["record_status"] == "FROZEN_GATE_A_PASS"
    assert record["preregistration"]["preregistration_merge_commit"] == (
        "b8f4773749cd5ed1b6e80decd80b1e126c524904"
    )
    assert record["execution_evidence"]["disposable_commit"] == (
        "1c258e3115d4f8d2d628b5cd248b89d6b067badb"
    )
    assert record["execution_evidence"]["workflow_run_id"] == 32948196961
    assert record["execution_evidence"]["workflow_job_id"] == 98113453104
    assert record["execution_evidence"]["full_suite_result"] == "3109 passed in 9.13s"
    assert record["historical_integrity"]["product11_gate_a_result_reused_as_current_proof"] is False


def test_product12_gate_a_root_outcomes_match_authoritative_run() -> None:
    record = _load(GATE_A_PATH)
    results = {item["root"]: item for item in record["root_results"]}

    assert results["https://irdai.gov.in/non-life-insurers1"]["outcome"] == (
        "DIRECT_HTTP_AVAILABLE"
    )
    assert results["https://irdai.gov.in/health-insurers1"]["outcome"] == (
        "DIRECT_HTTP_AVAILABLE"
    )
    bima = results["https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount"]
    assert bima["outcome"] == "ALL_ALLOWED_TRANSPORTS_FAILED"
    assert bima["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert record["gate_decision"]["passing_roots"] == 2
    assert record["gate_decision"]["decision"] == "PASS"


def test_product12_gate_a_preserves_zero_semantic_and_screening_activity() -> None:
    record = _load(GATE_A_PATH)
    metrics = record["method_metrics"]
    assert metrics["search_engine_queries"] == 0
    assert metrics["ad_hoc_transport_attempts"] == 0
    assert metrics["semantic_inspection"] == 0
    assert metrics["product_screening_started"] is False
    assert metrics["target_clause_reads"] == 0
    assert record["experiment"]["gate_b_started"] is False
    assert record["experiment"]["gate_c_started"] is False
    assert record["historical_integrity"]["motor_authorized"] is False


def test_gate_b_authorization_is_sequenced_after_gate_a_freeze_merge() -> None:
    auth = _load(GATE_B_AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_GATE_A_FREEZE_MERGE"
    assert auth["authorized_gate"] == "B"
    assert auth["gate_c_authorized"] is False
    assert auth["product_screening_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["gate_b_scope"]
    assert scope["historical_product11_gate_b_result_may_substitute"] is False
    assert scope["raw_destination_url_may_cross_boundary"] is False
    assert scope["anchor_text_may_cross_boundary"] is False
    assert scope["semantic_evidence_may_cross_boundary"] is False
    assert scope["product_detail_or_policy_wording_authorized"] is False
