from __future__ import annotations

import json
from pathlib import Path


GATE_B_PATH = Path(
    "docs/architecture/health_product12_gate_b_blind_path_discovery_2026-08-26.json"
)
GATE_C_AUTH_PATH = Path(
    "docs/architecture/health_product12_gate_c_execution_authorization_v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product12_gate_b_freezes_fresh_pass_evidence() -> None:
    record = _load(GATE_B_PATH)
    assert record["record_status"] == "FROZEN_GATE_B_PASS"
    assert record["execution_evidence"]["gate_a_freeze_merge_commit"] == (
        "afa780ff7b4a9cb4c01b5df60275cae5ab1c7400"
    )
    assert record["execution_evidence"]["disposable_commit"] == (
        "e921413ba9202b0b802fffcf3f93b5b8933f59dd"
    )
    assert record["execution_evidence"]["workflow_run_id"] == 32948896027
    assert record["execution_evidence"]["workflow_job_id"] == 98115621081
    assert record["execution_evidence"]["full_suite_result"] == "3113 passed in 9.08s"
    assert record["historical_integrity"]["product11_gate_b_result_reused_as_current_proof"] is False


def test_product12_gate_b_pass_and_blindness_metrics_match_authoritative_run() -> None:
    record = _load(GATE_B_PATH)
    result = record["blind_directory_result"]
    assert result["decision"] == "PASS"
    assert result["directory_projection_count"] == 10
    assert result["directory_capture_count"] == 10
    assert result["resolved_candidate_ids"] == ["chola", "magma", "navi", "shriram"]
    assert result["passing_candidate_ids"] == ["shriram"]
    assert result["shriram_blind_projection_count"] == 7

    metrics = record["blindness_metrics"]
    zero_fields = [
        "raw_regulator_destination_urls_emitted",
        "raw_insurer_origins_emitted",
        "raw_insurer_destination_urls_emitted",
        "anchor_text_emitted",
        "body_text_emitted",
        "page_titles_emitted",
        "screenshots_emitted",
        "target_clause_reads",
    ]
    assert all(metrics[field] == 0 for field in zero_fields)
    assert metrics["product_screening_started"] is False
    assert metrics["product_selected"] is False
    assert metrics["gate_c_started"] is False


def test_gate_c_authorization_uses_repaired_v2_selector_boundary() -> None:
    auth = _load(GATE_C_AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_GATE_B_FREEZE_MERGE"
    assert auth["authorized_gate"] == "C"
    scope = auth["gate_c_scope"]
    assert scope["selector_discovery_input_contract"] == "blind_discovery_link_metadata_v1"
    assert scope["selector_product_metadata_input_contract"] == "blind_preselection_product_metadata_v2"
    assert scope["selector_may_receive_raw_url_or_anchor_text"] is False
    assert scope["selector_may_receive_raw_parsed_file_path"] is False
    assert scope["selector_may_receive_raw_page_or_product_signal_output"] is False
    assert scope["selector_may_receive_semantic_bucket_presence_or_counts"] is False
    assert scope["source_ref_may_establish_authority_or_currentness_by_itself"] is False


def test_gate_c_authorization_preserves_post_selection_and_motor_guards() -> None:
    gate_b = _load(GATE_B_PATH)
    auth = _load(GATE_C_AUTH_PATH)
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    assert auth["gate_c_scope"]["semantic_fit_may_affect_selection"] is False
    assert auth["gate_c_scope"]["selection_override_authorized"] is False
    assert auth["gate_c_scope"]["post_selection_product_or_version_substitution_authorized"] is False
    assert auth["post_selection_guard"]["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert gate_b["historical_integrity"]["motor_authorized"] is False
