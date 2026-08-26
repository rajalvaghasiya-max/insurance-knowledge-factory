import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = ROOT / "docs/architecture/health_product13_gate_a_root_transport_fitness_2026-08-26.json"
AUTH_PATH = ROOT / "docs/architecture/health_product13_gate_b_execution_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product13_gate_a_fresh_evidence_is_pinned() -> None:
    freeze = _load(FREEZE_PATH)
    evidence = freeze["execution_evidence"]
    assert freeze["record_status"] == "FROZEN_GATE_A_PASS_PENDING_MERGE"
    assert freeze["preregistration"]["preregistration_merge_commit"] == "9bcf97ce9e382825c80e8a7755a2f0be02f2444f"
    assert evidence["disposable_commit"] == "e89b017fce4985819a8c588fa542f9c733112c97"
    assert evidence["workflow_run_id"] == 32951988717
    assert evidence["workflow_job_id"] == 98125220978
    assert evidence["full_suite_result"] == "3155 passed in 9.33s"
    assert evidence["disposable_branch_may_merge"] is False


def test_product13_gate_a_pass_preserves_frozen_transport_order() -> None:
    freeze = _load(FREEZE_PATH)
    assert freeze["gate_decision"]["decision"] == "PASS"
    assert freeze["frozen_transport_sequence"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    results = freeze["root_results"]
    assert [item["outcome"] for item in results] == [
        "DIRECT_HTTP_AVAILABLE",
        "DIRECT_HTTP_AVAILABLE",
        "ALL_ALLOWED_TRANSPORTS_FAILED",
    ]
    assert freeze["method_metrics"]["search_engine_queries"] == 0
    assert freeze["method_metrics"]["ad_hoc_transport_attempts"] == 0
    assert freeze["method_metrics"]["semantic_inspection"] == 0
    assert freeze["method_metrics"]["target_clause_reads"] == 0


def test_gate_b_authorization_is_narrow_and_fresh() -> None:
    auth = _load(AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_GATE_A_FREEZE_MERGE"
    assert auth["authorized_gate"] == "B"
    assert auth["gate_c_authorized"] is False
    assert auth["product_screening_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["gate_b_scope"]
    assert scope["historical_product12_gate_b_result_may_substitute"] is False
    assert scope["raw_destination_url_may_cross_boundary"] is False
    assert scope["anchor_text_may_cross_boundary"] is False
    assert scope["semantic_evidence_may_cross_boundary"] is False


def test_product11_product12_and_motor_remain_closed() -> None:
    freeze = _load(FREEZE_PATH)
    history = freeze["historical_integrity"]
    assert history["product12_gate_a_result_reused_as_current_proof"] is False
    assert history["product12_reopened_or_retried"] is False
    assert history["product11_reopened_or_retried"] is False
    assert history["motor_authorized"] is False
