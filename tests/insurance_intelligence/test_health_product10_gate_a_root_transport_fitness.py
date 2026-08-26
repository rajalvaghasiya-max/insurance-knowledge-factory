import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "docs" / "architecture" / "health_product10_gate_a_root_transport_fitness_2026-08-26.json"


def _load() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_gate_a_exact_roots_and_outcomes_are_frozen() -> None:
    result = _load()
    roots = result["root_results"]
    assert [item["root"] for item in roots] == [
        "https://irdai.gov.in/non-life-insurers1",
        "https://irdai.gov.in/health-insurers1",
        "https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount",
    ]
    assert [item["outcome"] for item in roots] == [
        "DIRECT_HTTP_AVAILABLE",
        "DIRECT_HTTP_AVAILABLE",
        "ALL_ALLOWED_TRANSPORTS_FAILED",
    ]


def test_gate_a_transport_attempts_follow_frozen_order() -> None:
    result = _load()
    roots = result["root_results"]
    assert result["allowed_transport_sequence"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]
    assert roots[0]["capture_strategy_attempted"] == ["static_http"]
    assert roots[1]["capture_strategy_attempted"] == ["static_http"]
    assert roots[2]["capture_strategy_attempted"] == [
        "static_http",
        "playwright_headless",
        "playwright_visible",
    ]


def test_gate_a_pass_is_based_on_preregistered_minimum_condition() -> None:
    decision = _load()["gate_decision"]
    assert decision["passing_roots"] == 2
    assert decision["failing_roots"] == 1
    assert decision["decision"] == "PASS"
    assert decision["next_gate"] == "GATE_B_BLIND_METADATA_PATH_DISCOVERY_FITNESS"
    assert decision["gate_c_authorized"] is False
    assert decision["insurer_or_product_screening_authorized_by_this_record"] is False


def test_gate_a_preserves_blindness_and_no_screening() -> None:
    result = _load()
    experiment = result["experiment"]
    metrics = result["blindness_and_method_metrics"]
    assert experiment["product_selected"] is False
    assert experiment["gate_b_started"] is False
    assert experiment["gate_c_started"] is False
    assert experiment["target_clause_reads"] == 0
    assert metrics["search_engine_fallbacks"] == 0
    assert metrics["ad_hoc_transport_attempts"] == 0
    assert metrics["gate_b_operator_raw_capture_reads"] == 0
    assert metrics["gate_b_selector_raw_capture_reads"] == 0
    assert metrics["insurer_screening_started"] is False
    assert metrics["product_screening_started"] is False
    assert metrics["target_clause_reads"] == 0


def test_gate_a_execution_lineage_is_auditable_and_non_merged() -> None:
    lineage = _load()["execution_lineage"]
    assert lineage["execution_mode"] == "disposable_non_merged_github_actions_smoke"
    assert lineage["smoke_branch"] == "product10-gate-a-live-smoke"
    assert lineage["smoke_commit"] == "4267e324791961f0cb3433fe1f04a1b1a5bbe4cb"
    assert lineage["workflow_run_id"] == 32938095594
    assert lineage["workflow_job_id"] == 98083250521
    assert lineage["workflow_conclusion"] == "success"
    assert lineage["factory_tests_after_smoke"] == 3048
    assert lineage["factory_tests_conclusion"] == "passed"
    assert lineage["smoke_branch_may_merge"] is False


def test_later_product10_transport_observation_does_not_rewrite_product9() -> None:
    history = _load()["historical_comparability"]
    assert history["product9_direct_root_403_observation_remains_immutable"] is True
    assert history["product9_is_reopened_repaired_or_reinterpreted"] is False
    assert history["product10_observation_date"] == "2026-08-26"
