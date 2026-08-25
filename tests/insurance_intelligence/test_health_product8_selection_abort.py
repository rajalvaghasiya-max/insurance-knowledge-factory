import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ABORT = ROOT / "docs/architecture/health_product8_selection_abort_2026-08-25.json"
PROTOCOL = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v5_product8.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_product8_aborts_before_selection_and_semantic_review() -> None:
    abort = _load(ABORT)
    state = abort["selection_state"]
    assert abort["record_status"] == "IMMUTABLE_EXPERIMENT_CLOSURE"
    assert abort["product_number"] == 8
    assert state["product_selected"] is False
    assert state["selection_record_created"] is False
    assert state["product_document_acquisition_started"] is False
    assert state["target_concept_semantic_review_started"] is False
    assert state["scoring_started"] is False


def test_product8_reconciles_full_current_insurer_universe() -> None:
    abort = _load(ABORT)
    universe = abort["insurer_universe"]
    ledger = abort["screening_ledger"]
    assert universe["general_insurer_count"] == 27
    assert universe["standalone_health_insurer_count"] == 6
    assert universe["total_insurer_count"] == 33
    assert universe["universe_reconciled_before_abort"] is True
    assert len(ledger) == 33
    assert len({row["insurer"] for row in ledger}) == 33


def test_every_product8_insurer_has_a_fail_closed_preselection_status() -> None:
    allowed_statuses = {
        "EXCLUDED_PRIOR_TARGET_CONCEPT_CONTAMINATION",
        "EXCLUDED_PRIOR_COLD_START",
        "EXCLUDED_NO_QUALIFYING_RETAIL_HEALTH_INDEMNITY_PRODUCT",
        "EXCLUDED_METADATA_CURRENTNESS_INSUFFICIENT",
        "EXCLUDED_PRODUCT8_PRESELECTION_CONTAMINATION",
    }
    ledger = _load(ABORT)["screening_ledger"]
    assert {row["status"] for row in ledger} <= allowed_statuses
    assert all(row["status"].startswith("EXCLUDED_") for row in ledger)


def test_product8_abort_is_unscored_and_cannot_be_repaired_retroactively() -> None:
    decision = _load(ABORT)["abort_decision"]
    assert decision["status"] == "SELECTION_UNIVERSE_EXHAUSTED_NO_ELIGIBLE_UNCONTAMINATED_CURRENTNESS_CORROBORATED_PRODUCT"
    assert decision["scoring_status"] == "UNSCORED"
    assert decision["semantic_outcome"] == "NOT_EVALUATED"
    assert decision["relax_product8_firewall_authorized"] is False
    assert decision["revive_quarantined_insurer_for_product8_authorized"] is False
    assert decision["select_after_abort_authorized"] is False
    assert decision["retroactive_product8_selection_authorized"] is False
    assert decision["motor_gate_authorized"] is False


def test_search_discovery_finding_is_future_protocol_input_not_product8_repair() -> None:
    finding = _load(ABORT)["methodology_finding"]
    assert finding["finding"] == "SEARCH_ENGINE_DISCOVERY_IS_TOO_CONTAMINATION_PRONE_FOR_V5_PRESELECTION"
    assert finding["future_change_is_not_product8_repair"] is True
    assert "direct-source metadata traversal strategy" in finding["future_protocol_implication"]


def test_product8_closure_preserves_v5_and_requires_new_preregistration() -> None:
    abort = _load(ABORT)
    protocol = _load(PROTOCOL)
    governance = abort["governance"]
    assert abort["protocol_path"].endswith("health_post_hc1_neutral_cold_start_protocol_v5_product8.json")
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT8_SELECTION"
    assert governance["product8_history_is_immutable"] is True
    assert governance["product8_does_not_satisfy_repeatability_success_bar"] is True
    assert governance["product8_does_not_falsify_semantic_repeatability"] is True
    assert governance["product8_does_not_authorize_motor"] is True
    assert governance["next_experiment_requires_new_preregistration_before_any_new_screening"] is True
