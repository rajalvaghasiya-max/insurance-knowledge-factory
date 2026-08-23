from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "docs/architecture/health_product5_selection_niva_bupa_reassure_3_0_2026-08-23.json"


def test_product5_selection_is_locked_to_v2_protocol_before_semantic_review() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))

    assert data["repeatability_protocol_path"] == "docs/architecture/health_repeatability_test_protocol_v2.json"
    assert data["repeatability_baseline_commit"] == "ee82220ef8ccca586f5e5760bf937c51644c712b"
    assert data["selected_product"]["uin"] == "NBHHLIP26047V012526"
    assert data["prior_repository_exposure"]["exact_uin_found"] is False
    assert data["prior_repository_exposure"]["governed_product_evidence_found"] is False
    assert data["experiment_boundaries"]["generic_runtime_remains_frozen"] is True
    assert data["experiment_boundaries"]["semantic_fit_assessment_after_selection_only"] is True
    assert data["experiment_boundaries"]["runtime_extension_before_initial_scoring_authorized"] is False
    assert data["experiment_boundaries"]["decision_logic_in_config_authorized"] is False
    assert data["experiment_boundaries"]["classification_rubric_version"] == "v2"


def test_product5_selection_does_not_encode_target_concept_result() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(data).lower()

    assert '"classification": "reuse"' not in serialized
    assert '"classification": "config_spec"' not in serialized
    assert '"classification": "representation_gap"' not in serialized
    assert '"classification": "knowledge_gap"' not in serialized
    assert '"percentage"' not in serialized
    assert '"waiting_period_type"' not in serialized
