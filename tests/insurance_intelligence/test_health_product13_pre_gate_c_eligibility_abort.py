import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABORT_PATH = ROOT / "docs/architecture/health_product13_pre_gate_c_eligibility_contract_abort_2026-08-26.json"
AUTH_PATH = ROOT / "docs/architecture/health_preselection_product_eligibility_projection_fitness_review_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product13_closes_unscored_before_gate_c_starts() -> None:
    record = _load(ABORT_PATH)
    exp = record["experiment"]
    assert record["record_status"] == "PRODUCT13_CLOSED_EXPERIMENT_UNSCORED"
    assert exp["gate_a_status"] == "PASS"
    assert exp["gate_b_status"] == "PASS"
    assert exp["gate_c_started"] is False
    assert exp["product_screening_started"] is False
    assert exp["product_selected"] is False
    assert exp["semantic_review_started"] is False
    assert exp["target_clause_reads"] == 0
    assert exp["outcome"] == "EXPERIMENT_UNSCORED"


def test_abort_is_exactly_missing_selector_safe_product_eligibility_evidence() -> None:
    record = _load(ABORT_PATH)
    reason = record["abort_reason"]
    assert reason["type"] == "PREREGISTERED_SELECTOR_ELIGIBILITY_CONTRACT_INSUFFICIENT"
    assert reason["selector_product_metadata_contract"] == "blind_preselection_product_metadata_v2"
    assert reason["selector_currentness_contract"] == "blind_product_identity_currentness_evidence_v1"
    missing = set(reason["missing_governed_selector_evidence"])
    assert "product_class_or_health_indemnity_classification" in missing
    assert "base_product_vs_rider_or_addon_classification" in missing
    assert "retail_availability_or_individual_family_floater_eligibility" in missing
    assert reason["gate_c_not_started_because_conflict_detected_pre_start"] is True


def test_product13_integrity_and_history_are_preserved() -> None:
    record = _load(ABORT_PATH)
    integrity = record["integrity"]
    interpretation = record["interpretation"]
    history = record["historical_integrity"]
    assert integrity["runtime_changed_after_gate_c_authorization"] is False
    assert integrity["selection_override_used"] is False
    assert integrity["product_document_acquisition_started"] is False
    assert integrity["semantic_fit_used"] is False
    assert integrity["target_clause_reads"] == 0
    assert interpretation["product13_may_be_retried"] is False
    assert interpretation["product13_protocol_may_be_mutated"] is False
    assert history["product11_reopened_or_retried"] is False
    assert history["product12_reopened_or_retried"] is False
    assert history["motor_authorized"] is False


def test_next_authorization_is_fitness_review_only() -> None:
    auth = _load(AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_PRODUCT13_CLOSURE_MERGE"
    assert auth["authorized_next_action"] == "HEALTH_PRESELECTION_PRODUCT_ELIGIBILITY_PROJECTION_FITNESS_REVIEW_ONLY"
    assert auth["product14_preregistration_authorized"] is False
    assert auth["motor_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["review_scope"]
    assert scope["may_retry_product13"] is False
    assert scope["may_mutate_product13_protocol_v10"] is False
    assert scope["may_assess_missing_selector_safe_product_eligibility_evidence"] is True
    assert scope["may_design_prospective_generic_projection_repair"] is True
    assert scope["may_add_product_specific_selection_heuristics"] is False
