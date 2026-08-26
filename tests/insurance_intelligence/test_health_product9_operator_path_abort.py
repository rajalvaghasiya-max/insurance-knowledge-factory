from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "docs" / "architecture" / "health_product9_selection_abort_operator_path_2026-08-26.json"


def _load() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_product9_closes_unselected_and_unscored() -> None:
    payload = _load()
    assert payload["selection_state"] == "UNSELECTED"
    assert payload["outcome"] == "EXPERIMENT_UNSCORED"
    assert payload["closure_reason"] == "PRE_RENDER_METADATA_PATH_UNAVAILABLE_FOR_ALL_PREREGISTERED_RETRY_INSURERS"


def test_all_retry_insurers_failed_closed_without_rendering() -> None:
    payload = _load()
    results = payload["candidate_pre_render_results"]
    assert len(results) == 4
    assert all(item["rendered"] is False for item in results)
    assert all(item["result"] == "FAIL_CLOSED_OPERATOR_PATH" for item in results)
    assert all(item["pre_render_classification"] == "UNCLASSIFIABLE_AS_METADATA_FROM_ALLOWED_PRE_RENDER_SIGNALS" for item in results)


def test_403_roots_did_not_trigger_search_fallback() -> None:
    payload = _load()
    unavailable = [item for item in payload["root_observations"] if item["status"] == "PREREGISTERED_ROOT_UNAVAILABLE_403"]
    assert len(unavailable) == 2
    assert all(item["search_fallback_used"] is False for item in unavailable)


def test_blindness_metrics_remain_zero() -> None:
    metrics = _load()["blindness_metrics"]
    assert metrics == {
        "insurer_origins_rendered": 0,
        "product_documents_opened": 0,
        "preselection_target_clause_reads": 0,
        "search_engine_fallbacks": 0,
        "selection_overrides": 0,
        "product_or_version_substitutions": 0,
    }


def test_abort_cannot_satisfy_motor_gate_or_semantic_repeatability() -> None:
    interpretation = _load()["interpretation"]
    assert interpretation["semantic_repeatability_inference_authorized"] is False
    assert interpretation["currentness_inference_authorized"] is False
    assert interpretation["motor_gate_satisfied"] is False
    assert interpretation["retroactive_protocol_relaxation_authorized"] is False
    assert interpretation["retroactive_candidate_substitution_authorized"] is False
