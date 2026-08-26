from __future__ import annotations

import json
from pathlib import Path


REVIEW_PATH = Path(
    "docs/architecture/health_preselection_currentness_path_fitness_review_2026-08-26.json"
)
AUTH_PATH = Path(
    "docs/architecture/health_identity_currentness_acquisition_repair_authorization_v1.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_review_preserves_product11_and_product12_immutability() -> None:
    review = _load(REVIEW_PATH)
    scope = review["scope"]
    assert review["record_status"] == "FROZEN_FITNESS_REVIEW_PENDING_MERGE"
    assert scope["products_reviewed"] == [11, 12]
    assert scope["product11_may_be_changed_or_retried"] is False
    assert scope["product12_may_be_changed_or_retried"] is False
    assert scope["product13_preregistration_authorized"] is False
    assert scope["motor_authorized"] is False


def test_review_separates_v2_boundary_from_identity_currentness_gap() -> None:
    review = _load(REVIEW_PATH)
    findings = review["runtime_boundary_findings"]
    diagnosis = review["diagnosis"]
    assert findings["v2_projection_boundary_fitness"] == "FIT"
    assert findings["uin_extractor_scope"] == "LABEL_LED_TEXT_ONLY"
    assert diagnosis["classification"] == (
        "SYSTEMATIC_PRESELECTION_IDENTITY_CURRENTNESS_ACQUISITION_GAP"
    )
    assert diagnosis["not_a_semantic_gap"] is True
    assert diagnosis["not_a_v2_blindness_gap"] is True
    assert diagnosis["not_a_current_product_eligibility_gate_gap"] is True


def test_review_does_not_overclaim_site_specific_absence() -> None:
    review = _load(REVIEW_PATH)
    diagnosis = review["diagnosis"]
    assert diagnosis["site_specific_evidence_scarcity_also_present"] is True
    assert diagnosis["not_proof_that_shriram_has_no_qualifying_product"] is True
    assert diagnosis["not_proof_that_any_candidate_insurer_has_no_qualifying_product"] is True


def test_required_capability_sits_before_selection_and_preserves_blindness() -> None:
    review = _load(REVIEW_PATH)
    capability = review["required_prospective_capability"]
    assert capability["position_in_pipeline"] == (
        "after authorized blind metadata-path discovery and before neutral product selection"
    )
    responsibilities = set(capability["minimum_responsibilities"])
    assert "enforce bounded depth and deterministic traversal order" in responsibilities
    assert any("raw-location-free" in item for item in responsibilities)
    assert any("fail closed" in item for item in responsibilities)


def test_next_authorization_is_repair_only_not_product13_or_motor() -> None:
    auth = _load(AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_FITNESS_REVIEW_MERGE"
    assert auth["authorized_next_action"] == (
        "PROSPECTIVE_IDENTITY_CURRENTNESS_ACQUISITION_REPAIR_ONLY"
    )
    assert auth["product13_preregistration_authorized"] is False
    assert auth["motor_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["repair_scope"]
    assert scope["may_retry_product11"] is False
    assert scope["may_retry_product12"] is False
    assert scope["may_preregister_product13_before_repair_freeze"] is False
    assert scope["may_change_v2_to_allow_raw_url_anchor_or_parsed_path"] is False
