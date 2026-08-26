import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE_PATH = ROOT / "docs/architecture/health_product13_gate_b_blind_path_discovery_2026-08-26.json"
AUTH_PATH = ROOT / "docs/architecture/health_product13_gate_c_execution_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product13_gate_b_fresh_evidence_is_pinned() -> None:
    freeze = _load(FREEZE_PATH)
    evidence = freeze["execution_evidence"]
    assert freeze["record_status"] == "FROZEN_GATE_B_PASS_PENDING_MERGE"
    assert evidence["gate_a_freeze_merge_commit"] == "249abf4a8750c4818f1e83d61c5d0262b3cf289c"
    assert evidence["disposable_commit"] == "ed4396e1153ee13b7c983579824884bd3d51f6a9"
    assert evidence["workflow_run_id"] == 32956218362
    assert evidence["workflow_job_id"] == 98138351773
    assert evidence["full_suite_result"] == "3159 passed in 8.07s"
    assert evidence["disposable_branch_may_merge"] is False


def test_product13_gate_b_pass_is_blind_and_fresh() -> None:
    freeze = _load(FREEZE_PATH)
    result = freeze["blind_directory_result"]
    assert result["decision"] == "PASS"
    assert result["directory_projection_count"] == 10
    assert result["directory_capture_count"] == 10
    assert result["resolved_candidate_ids"] == ["chola", "magma", "navi", "shriram"]
    assert result["passing_candidate_ids"] == ["shriram"]
    assert result["shriram_blind_projection_count"] == 7
    metrics = freeze["blindness_metrics"]
    for key in (
        "raw_regulator_destination_urls_emitted",
        "raw_insurer_origins_emitted",
        "raw_insurer_destination_urls_emitted",
        "anchor_text_emitted",
        "body_text_emitted",
        "page_titles_emitted",
        "screenshots_emitted",
        "target_clause_reads",
    ):
        assert metrics[key] == 0
    assert metrics["product_screening_started"] is False
    assert metrics["product_selected"] is False
    assert metrics["semantic_review_started"] is False
    assert metrics["gate_c_started"] is False
    assert freeze["historical_integrity"]["product12_gate_b_result_reused_as_current_proof"] is False


def test_product13_gate_c_uses_frozen_identity_currentness_repair() -> None:
    auth = _load(AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_GATE_B_FREEZE_MERGE"
    assert auth["authorized_gate"] == "C"
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["gate_c_scope"]
    assert scope["selector_discovery_input_contract"] == "blind_discovery_link_metadata_v1"
    assert scope["selector_product_metadata_input_contract"] == "blind_preselection_product_metadata_v2"
    assert scope["selector_currentness_input_contract"] == "blind_product_identity_currentness_evidence_v1"
    assert scope["identity_currentness_acquirer"] == "GovernedProductIdentityCurrentnessEvidenceAcquirer"
    assert scope["bounded_machine_side_metadata_traversal_required"] is True
    assert scope["authorized_metadata_artifact_classes_only"] is True
    assert scope["exact_product_uin_ambiguity_fails_closed"] is True
    assert scope["source_ref_may_establish_authority_or_currentness_by_itself"] is False


def test_product13_gate_c_keeps_semantic_and_history_guards_closed() -> None:
    auth = _load(AUTH_PATH)
    scope = auth["gate_c_scope"]
    assert scope["selector_may_receive_raw_url_or_anchor_text"] is False
    assert scope["selector_may_receive_raw_parsed_file_path"] is False
    assert scope["selector_may_receive_raw_page_or_product_signal_output"] is False
    assert scope["selector_may_receive_semantic_bucket_presence_or_counts"] is False
    assert scope["semantic_fit_may_affect_selection"] is False
    assert scope["selection_override_authorized"] is False
    assert scope["post_selection_product_or_version_substitution_authorized"] is False
    guard = auth["post_selection_guard"]
    assert guard["product_document_acquisition_before_selection_freeze"] is False
    assert guard["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert guard["semantic_review_before_positive_currentness_eligibility"] is False
    freeze = _load(FREEZE_PATH)
    history = freeze["historical_integrity"]
    assert history["product12_reopened_or_retried"] is False
    assert history["product11_reopened_or_retried"] is False
    assert history["motor_authorized"] is False
