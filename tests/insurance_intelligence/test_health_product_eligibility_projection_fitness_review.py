import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW_PATH = ROOT / "docs/architecture/health_preselection_product_eligibility_projection_fitness_review_2026-08-26.json"
AUTH_PATH = ROOT / "docs/architecture/health_product_eligibility_projection_repair_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_fitness_review_is_pinned_to_product13_closure() -> None:
    review = _load(REVIEW_PATH)
    assert review["record_status"] == "FROZEN_FITNESS_VERDICT_PENDING_MERGE"
    assert review["product13_closure_merge_commit"] == "a311a9ddc441c520daa4c7e4baeb4ab6f103fa6d"
    assert review["verdict"] == "GENERIC_SELECTOR_CONTRACT_GAP"


def test_current_contracts_are_sound_but_incomplete() -> None:
    review = _load(REVIEW_PATH)
    evidence = review["evidence"]
    assert evidence["identity_currentness_acquirer_fitness"] == "SOUND_BUT_INCOMPLETE"
    assert "Health indemnity product class" in evidence["current_contracts_cannot_prove"]
    assert "base product versus rider or add-on status" in evidence["current_contracts_cannot_prove"]
    assert "family-floater purchase availability" in evidence["current_contracts_cannot_prove"]
    assert evidence["source_asset_classifier_fitness"] == "INSUFFICIENT_FOR_SELECTOR_ELIGIBILITY"
    assert evidence["product_signal_extractor_fitness"] == "NOT_SELECTOR_SAFE_FOR_THIS_PURPOSE"


def test_prospective_repair_is_generic_source_grounded_and_fail_closed() -> None:
    review = _load(REVIEW_PATH)
    repair = review["prospective_repair_shape"]
    assert repair["repair_type"] == "GENERIC_PRODUCT_ELIGIBILITY_EVIDENCE_PROJECTION"
    assert repair["must_be_source_grounded"] is True
    assert repair["must_use_explicit_metadata_evidence_only"] is True
    assert repair["must_fail_closed_on_missing_or_conflicting_evidence"] is True
    assert repair["must_not_infer_from_product_name_alone"] is True
    assert repair["must_not_infer_from_raw_url_or_path_alone"] is True
    assert repair["must_not_use_target_concept_semantics"] is True
    assert repair["must_not_expose_raw_page_text"] is True


def test_historical_experiments_and_future_domains_remain_closed() -> None:
    review = _load(REVIEW_PATH)
    history = review["historical_integrity"]
    assert history["product11_reopened_or_retried"] is False
    assert history["product12_reopened_or_retried"] is False
    assert history["product13_reopened_or_retried"] is False
    assert history["product13_gate_c_started"] is False
    assert history["product14_preregistration_authorized"] is False
    assert history["motor_authorized"] is False
    assert history["semantic_review_authorized"] is False
    assert history["target_clause_reads_authorized"] is False


def test_next_authorization_is_repair_only() -> None:
    auth = _load(AUTH_PATH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_FITNESS_REVIEW_MERGE"
    assert auth["authorized_next_action"] == "IMPLEMENT_GENERIC_HEALTH_PRODUCT_ELIGIBILITY_EVIDENCE_PROJECTION_ONLY"
    assert auth["product14_preregistration_authorized"] is False
    assert auth["motor_authorized"] is False
    assert auth["semantic_review_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    scope = auth["repair_scope"]
    assert scope["may_use_product_specific_heuristics"] is False
    assert scope["may_infer_eligibility_from_product_name_alone"] is False
    assert scope["may_infer_eligibility_from_raw_url_or_path_alone"] is False
    assert scope["may_expose_raw_page_text_to_selector"] is False
    assert scope["must_fail_closed_on_missing_or_conflicting_eligibility_evidence"] is True
    assert scope["must_not_modify_product11_product12_or_product13_results"] is True
