from __future__ import annotations

import json
from pathlib import Path

from insurance_intelligence.evaluation.dataset import load_evaluation_dataset
from insurance_intelligence.evaluation.scenarios import build_default_registry


RECORD_PATH = Path(
    "docs/architecture/insurance_intelligence/"
    "P2_5_ADVERSARIAL_EVALUATION_CLOSURE.json"
)
DATASET_PATH = Path("tests/fixtures/insurance_intelligence/llm_evaluation")


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_p2_5_closure_is_bounded_pass() -> None:
    record = _record()
    assert record["unit_id"] == "P2.5"
    assert record["decision"] == "PASS"
    assert record["scope"] == {
        "generic_capability": "PASS",
        "star_pilot_proof": "PASS",
        "legacy_bypass_inventory": "DEFERRED_TO_P2.6",
    }


def test_closure_matches_versioned_controlled_dataset() -> None:
    record = _record()
    dataset = load_evaluation_dataset(DATASET_PATH)
    summary = dataset.summary()["by_category"]

    assert record["dataset"]["dataset_id"] == dataset.dataset_id
    assert record["dataset"]["dataset_version"] == dataset.dataset_version
    assert record["dataset"]["case_count"] == len(dataset.cases) == 24
    assert record["dataset"]["category_counts"] == summary


def test_closure_covers_all_adversarial_cases_and_recommendation_case() -> None:
    record = _record()
    dataset = load_evaluation_dataset(DATASET_PATH)
    adversarial = tuple(case for case in dataset.cases if case.category.value == "ADVERSARIAL")

    assert tuple(record["dataset"]["star_adversarial_case_ids"]) == tuple(
        case.case_id for case in adversarial
    )
    recommendation = next(case for case in adversarial if case.case_id == "adv-007")
    assert record["dataset"]["unsupported_recommendation_case_id"] == recommendation.case_id
    assert "UNSUPPORTED_RECOMMENDATION" in recommendation.forbidden_behaviours
    assert recommendation.expected_outcome.value == "FAIL"


def test_closure_matches_complete_default_pipeline_catalogue() -> None:
    record = _record()
    scenarios = build_default_registry().all_scenarios()
    scenario_ids = tuple(item.scenario_id for item in scenarios)

    assert record["pipeline_catalogue"]["scenario_count"] == len(scenarios) == 11
    assert tuple(record["pipeline_catalogue"]["required_scenario_ids"]) == scenario_ids
    assert "unsupported_product_recommendation" in scenario_ids
    assert "star_copay_determinism" in scenario_ids


def test_closure_sources_exist_and_scope_boundaries_are_explicit() -> None:
    record = _record()
    assert all(Path(path).is_file() for path in record["source_references"])

    limitations = " ".join(record["limitations"]).lower()
    assert "does not guarantee claim payment" in limitations
    assert "does not certify product comparison" in limitations
    assert "p2.6" in limitations


def test_closure_record_contains_no_customer_answer_or_recommendation() -> None:
    record = _record()
    prohibited = {"answer", "final_answer", "preferred_product", "recommendation"}
    assert not prohibited.intersection(record)
