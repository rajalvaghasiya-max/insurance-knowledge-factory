import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "docs/architecture/tata_aig_medicare_premier_waiting_period_frozen_runtime_result_2026-08-23.json"


def _result():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_tata_waiting_period_passed_without_runtime_change() -> None:
    result = _result()
    attempt = result["initial_frozen_runtime_attempt"]
    assert attempt["runtime_files_added"] == 0
    assert attempt["runtime_loc_delta"] == 0
    assert attempt["product_specific_runtime_logic_added"] == 0
    assert attempt["decision_logic_added_in_config_or_fixtures"] == 0
    assert attempt["silent_semantic_coercions"] == 0
    live = result["live_result"]
    assert live["waiting_period_cases_passed"] == live["waiting_period_certification_cases"] == 7
    assert live["material_rule_cases_passed"] == live["material_rule_certification_cases"] == 2
    assert live["all_complete"] is True
    assert live["all_explanation_permitted"] is True


def test_tata_waiting_period_is_conservatively_scored_config_spec() -> None:
    classification = _result()["repeatability_classification"]
    assert classification["classification"] == "CONFIG_SPEC"
    assert classification["runtime_reuse_observed"] is True
    assert classification["new_semantic_schema_required"] is False
    assert classification["new_runtime_architecture_required"] is False
    assert _result()["governance"]["rubric_changed_after_observing_product"] is False
