import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "docs" / "architecture" / "health_product11_gate_a_root_transport_fitness_2026-08-26.json"


def _load() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_product11_gate_a_passes_and_only_gate_b_is_authorized() -> None:
    record = _load()
    experiment = record["experiment"]
    decision = record["gate_decision"]
    assert record["record_status"] == "FROZEN_GATE_A_PASS_GATE_B_AUTHORIZED"
    assert experiment["gate_a_status"] == "PASS"
    assert decision["condition_satisfied"] is True
    assert decision["decision"] == "PASS"
    assert decision["gate_b_authorized"] is True
    assert decision["gate_c_authorized"] is False
    assert decision["insurer_or_product_screening_authorized"] is False
    assert experiment["product_selected"] is False
    assert experiment["target_clause_reads"] == 0


def test_two_irdai_roots_are_currently_direct_http_available() -> None:
    results = _load()["root_results"]
    passing = [item for item in results if item["accepted"] is True]
    assert len(passing) == 2
    assert all(item["outcome"] == "DIRECT_HTTP_AVAILABLE" for item in passing)
    assert all(item["capture_strategy"] == "static_http" for item in passing)
    assert all(item["capture_strategy_attempted"] == ["static_http"] for item in passing)


def test_bima_bharosa_exhausted_only_the_frozen_transport_sequence() -> None:
    results = _load()["root_results"]
    bima = next(item for item in results if "bimabharosa" in item["root"])
    assert bima["accepted"] is False
    assert bima["outcome"] == "ALL_ALLOWED_TRANSPORTS_FAILED"
    assert bima["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]


def test_gate_a_lineage_and_zero_screening_metrics_are_frozen() -> None:
    record = _load()
    lineage = record["execution_lineage"]
    metrics = record["method_metrics"]
    assert lineage["smoke_branch"] == "product11-gate-a-live-smoke"
    assert lineage["smoke_commit"] == "d897d51f53ad6a074ceeab80bba78ba9300df8f0"
    assert lineage["workflow_run_id"] == 32943204503
    assert lineage["workflow_job_id"] == 98098341171
    assert lineage["factory_tests_after_smoke"] == 3072
    assert lineage["smoke_branch_may_merge"] is False
    assert metrics["search_engine_queries"] == 0
    assert metrics["search_engine_fallbacks"] == 0
    assert metrics["ad_hoc_transport_attempts"] == 0
    assert metrics["product_screening_started"] is False
    assert metrics["product_selected"] is False
    assert metrics["preselection_target_clause_reads"] == 0


def test_historical_results_not_reused_and_motor_stays_closed() -> None:
    record = _load()
    assert record["gate_decision"]["historical_root_observations_reused_as_current_proof"] is False
    history = record["historical_integrity"]
    assert history["product9_modified"] is False
    assert history["product10_modified"] is False
    assert history["motor_authorized"] is False
