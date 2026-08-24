import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SELECTION_PATH = ROOT / "docs/architecture/health_product7_selection_icici_lombard_arogya_sanjeevani_2026-08-24.json"


def _selection():
    return json.loads(SELECTION_PATH.read_text(encoding="utf-8"))


def test_product7_selection_is_icici_arogya_under_v4():
    selection = _selection()
    assert selection["selection_type"] == "health_product7_contamination_safe_cold_start_selection_v4"
    assert selection["selected_after_protocol_merge"] is True
    product = selection["selected_product"]
    assert product["insurer_id"] == "icici_lombard"
    assert product["product_id"] == "arogya_sanjeevani_policy"
    assert product["uin"] == "ICIHLIP20178V011920"


def test_selected_path_had_zero_target_clause_reads_and_no_product_document_opening():
    basis = _selection()["selection_basis"]
    assert basis["semantic_fit_reviewed_before_selection"] is False
    assert basis["selected_product_policy_wording_opened_before_selection_record"] is False
    assert basis["selected_product_prospectus_opened_before_selection_record"] is False
    assert basis["selected_product_cis_opened_before_selection_record"] is False
    assert basis["selected_product_target_clause_read_before_selection_record"] is False
    assert basis["selected_path_preselection_target_clause_reads"] == 0
    assert basis["selection_override_used"] is False


def test_candidate_insurer_target_snippets_are_quarantined_not_used_for_selected_path():
    quarantine = _selection()["quarantined_preselection_exposures"]
    assert quarantine["selected_path_exposures"] == 0
    assert set(quarantine["candidate_insurer_quarantines"]) == {
        "Aditya Birla Health Insurance Co. Ltd.",
        "Care Health Insurance Limited",
        "Generali Central Insurance Company Limited",
        "Go Digit General Insurance Limited",
    }
    assert "immediately excluded" in quarantine["accounting_basis"]
    assert "selected ICICI product" in quarantine["accounting_basis"]


def test_icici_is_first_nonexcluded_uncontaminated_insurer_in_recorded_screen():
    ledger = _selection()["insurer_screening_ledger"]
    assert ledger[-1]["insurer"] == "ICICI Lombard General Insurance Company Limited"
    assert ledger[-1]["status"] == "FIRST_ELIGIBLE_UNCONTAMINATED_INSURER"
    assert all(item["status"] != "FIRST_ELIGIBLE_UNCONTAMINATED_INSURER" for item in ledger[:-1])
    assert [item["insurer"] for item in ledger] == [
        "ACKO General Insurance Limited",
        "Aditya Birla Health Insurance Co. Ltd.",
        "Agriculture Insurance Company of India Limited",
        "Bajaj General Insurance Limited / Bajaj Allianz General Insurance Company Limited",
        "Care Health Insurance Limited",
        "Cholamandalam MS General Insurance Company Limited",
        "ECGC Limited",
        "Generali Central Insurance Company Limited",
        "Go Digit General Insurance Limited",
        "HDFC ERGO General Insurance Company Limited",
        "ICICI Lombard General Insurance Company Limited",
    ]


def test_selected_uin_is_clean_at_frozen_repository_baseline():
    checkpoint = _selection()["repository_exposure_checkpoint"]
    assert checkpoint["baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert checkpoint["exact_uin_query"] == "ICIHLIP20178V011920"
    assert checkpoint["exact_uin_hit"] is False
    assert checkpoint["product_identity_hit"] is False
    assert checkpoint["governed_product_evidence_found"] is False
    assert checkpoint["semantic_binding_found"] is False
    assert checkpoint["certification_fixture_found"] is False
    assert checkpoint["prior_cold_start_result_found"] is False


def test_lower_uin_metadata_ambiguities_are_not_silently_coerced_into_eligibility():
    ledger = _selection()["selected_insurer_metadata_ledger"]
    selected = [item for item in ledger["observed_current_or_non_archived_candidates"] if item["selection_status"] == "SELECTED"]
    assert selected == [{
        "product_name": "Arogya Sanjeevani Policy, ICICI Lombard",
        "uin": "ICIHLIP20178V011920",
        "metadata_status": "CURRENT_INSURER_RENEWAL_TABLE_AND_IRDAI_NON_ARCHIVED",
        "selection_status": "SELECTED",
    }]
    exclusions = {item["uin"]: item["reason"] for item in ledger["metadata_exclusions_relevant_to_lower_uin_check"]}
    assert "current-offering status is not metadata-verified" in exclusions["ICIHLIP20127V011920"]
    assert "current retail indemnity eligibility" in exclusions["ICIHLIP19050V011819"]


def test_selection_merge_is_required_before_semantic_review():
    governance = _selection()["governance"]
    assert governance["selection_record_must_merge_before_selected_product_document_opening"] is True
    assert governance["runtime_extension_before_initial_scoring_authorized"] is False
    assert governance["semantic_or_spec_extension_before_initial_scoring_authorized"] is False
    assert governance["motor_readiness_authorized"] is False
