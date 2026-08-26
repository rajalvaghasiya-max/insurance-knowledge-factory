import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUTH = ROOT / "docs" / "architecture" / "health_product11_gate_a_authorization_2026-08-26.json"


def _load() -> dict:
    return json.loads(AUTH.read_text(encoding="utf-8"))


def test_product11_gate_a_only_is_authorized() -> None:
    record = _load()
    experiment = record["experiment"]
    assert record["record_status"] == "GATE_A_AUTHORIZED_NOT_STARTED"
    assert experiment["product_number"] == 11
    assert experiment["gate_a_authorized"] is True
    assert experiment["gate_a_started"] is False
    assert experiment["gate_b_authorized"] is False
    assert experiment["gate_c_authorized"] is False
    assert experiment["product_screening_started"] is False
    assert experiment["product_selected"] is False
    assert experiment["target_clause_reads"] == 0


def test_authorization_is_bound_to_merged_green_preregistration() -> None:
    prereg = _load()["preregistration"]
    assert prereg["pr_number"] == 160
    assert prereg["merge_commit"] == "389fc99d0b4556d15e7bc7dcdb5c55af10ac8556"
    assert prereg["canonical_ci_passed"] == 3068
    assert prereg["semantic_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert prereg["experiment_harness_baseline_commit"] == "784602b79d976873216f297ab296836e91cfa1ec"


def test_gate_a_scope_cannot_leak_into_screening_or_later_gates() -> None:
    gate = _load()["gate_a_authorization"]
    assert gate["scope"] == "root_transport_fitness_only"
    assert gate["exact_roots_must_come_from_preregistered_protocol"] is True
    assert gate["allowed_transport_sequence_must_come_from_preregistered_protocol"] is True
    assert gate["historical_root_observations_are_current_proof"] is False
    assert gate["search_engine_fallback_authorized"] is False
    assert gate["ad_hoc_transport_authorized"] is False
    assert gate["gate_b_may_start_before_gate_a_result_is_frozen"] is False
    assert gate["gate_c_may_start_before_gate_a_and_gate_b_results_are_frozen"] is False
    assert gate["insurer_or_product_screening_authorized"] is False
    assert gate["semantic_inspection_authorized"] is False


def test_historical_experiments_and_motor_remain_closed() -> None:
    history = _load()["historical_integrity"]
    assert history["product9_reopened_or_retried"] is False
    assert history["product10_reopened_or_retried"] is False
    assert history["motor_authorized"] is False
