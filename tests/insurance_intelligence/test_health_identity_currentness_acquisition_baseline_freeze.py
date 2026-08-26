from __future__ import annotations

import json
from pathlib import Path


FREEZE_PATH = Path(
    "docs/architecture/health_identity_currentness_acquisition_baseline_freeze_2026-08-26.json"
)


def _load() -> dict:
    return json.loads(FREEZE_PATH.read_text(encoding="utf-8"))


def test_freeze_pins_exact_repair_merge_and_ci() -> None:
    record = _load()
    assert record["record_status"] == (
        "FROZEN_PROSPECTIVE_HEALTH_IDENTITY_CURRENTNESS_ACQUISITION_BASELINE_PENDING_MERGE"
    )
    assert record["repair_merge_commit"] == "5b71fc9e835e86055d1df31bbacf6c23375430bb"
    assert record["repair_pr"] == 172
    assert record["repair_branch_head"] == "c178043933af2ab78333e76a690f90cc651c9d76"
    assert record["repair_branch_ci"]["workflow_run_id"] == 32951178454
    assert record["repair_branch_ci"]["workflow_job_id"] == 98122664562
    assert record["repair_branch_ci"]["result"] == "3139 passed in 8.19s"


def test_freeze_pins_raw_location_free_contracts_and_fail_closed_rules() -> None:
    record = _load()
    components = record["baseline_components"]
    assert components["selector_projection_contract"] == "blind_preselection_product_metadata_v2"
    assert components["currentness_companion_projection_contract"] == (
        "blind_product_identity_currentness_evidence_v1"
    )
    props = record["frozen_properties"]
    assert props["generic_not_insurer_specific"] is True
    assert props["bounded_deterministic_traversal"] is True
    assert props["authorized_metadata_artifact_classes_only"] is True
    assert props["exact_product_uin_binding_ambiguity_fails_closed"] is True
    assert props["source_ref_is_distinctness_only_not_authority_or_currentness"] is True
    assert props["selector_raw_url_anchor_path_body_screenshot_semantic_fields_forbidden"] is True


def test_freeze_preserves_zero_target_reads_and_historical_integrity() -> None:
    record = _load()
    props = record["frozen_properties"]
    assert props["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert props["policy_wording_prospectus_cis_semantic_inspection_before_selection_authorized"] is False
    history = record["historical_integrity"]
    assert history["product11_immutable"] is True
    assert history["product12_immutable"] is True
    assert history["product11_retry_authorized"] is False
    assert history["product12_retry_authorized"] is False
    assert history["motor_authorized"] is False


def test_product13_design_only_becomes_possible_after_freeze_merge() -> None:
    record = _load()
    auth = record["next_authorization"]
    assert auth["effective_only_after_this_baseline_freeze_merges_green"] is True
    assert auth["product13_preregistration_may_be_designed_after_merge"] is True
    assert auth["product13_execution_authorized_by_this_record"] is False
    assert auth["semantic_review_authorized_by_this_record"] is False
    assert auth["target_clause_reads_authorized_by_this_record"] is False
    assert auth["motor_authorized_by_this_record"] is False
    assert auth["required_product13_baseline_anchor"] == "merge commit of this baseline-freeze PR"
