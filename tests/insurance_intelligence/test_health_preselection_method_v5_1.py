import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
METHOD = ROOT / "docs/architecture/health_neutral_preselection_method_v5_1.json"
LEDGER = ROOT / "docs/architecture/POLICYSCNA_EXECUTION_LEDGER.md"


def _load() -> dict:
    return json.loads(METHOD.read_text(encoding="utf-8"))


def test_v5_1_is_locked_before_product9_and_forbids_search_result_screening() -> None:
    method = _load()
    boundary = method["method_boundary"]
    assert method["record_status"] == "LOCKED_BEFORE_ANY_PRODUCT9_SCREENING"
    assert boundary["broad_search_engine_candidate_discovery_after_experiment_lock"] is False
    assert boundary["search_result_snippets_as_selection_evidence"] is False
    assert boundary["direct_source_roots_only"] is True
    assert boundary["selector_input_contract"] == "blind_preselection_product_metadata_v1"


def test_selector_information_firewall_forbids_semantic_presence_signals() -> None:
    firewall = _load()["information_firewall"]
    forbidden = set(firewall["forbidden_selector_information"])
    assert "waiting-period signals" in forbidden
    assert "copayment mechanics" in forbidden
    assert "UIN evidence_text" in forbidden
    assert firewall["semantic_bucket_presence_or_counts_may_influence_selection"] is False
    assert firewall["semantic_content_changes_with_identical_identity_metadata_must_not_change_projection"] is True


def test_product8_remains_immutable_and_product9_stays_blocked() -> None:
    method = _load()
    history = method["product8_immutability"]
    gate = method["next_experiment_gate"]
    ledger = LEDGER.read_text(encoding="utf-8")
    assert history["product8_quarantines_are_reversed"] is False
    assert history["product8_may_be_rescored_or_reselected"] is False
    assert history["v5_1_is_a_future_method_change_not_a_product8_repair"] is True
    assert gate["product9_screening_authorized_by_this_record_alone"] is False
    assert gate["motor_authorized"] is False
    assert "No Product #9 candidate screening is authorized" in ledger
    assert "Motor gate remains **CLOSED**" in ledger
