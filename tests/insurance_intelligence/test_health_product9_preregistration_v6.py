import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v6_product9.json"


def _load() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_product9_is_locked_before_screening_with_exact_direct_roots() -> None:
    protocol = _load()
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT9_SCREENING"
    assert protocol["experiment"]["product_number"] == 9
    assert protocol["experiment"]["product_selected"] is False
    assert protocol["semantic_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert protocol["selection_method_baseline_commit"] == "d7dc909696670f77d0db565fc8855820775e53f2"
    assert protocol["exact_direct_source_roots"] == [
        "https://irdai.gov.in/non-life-insurers1",
        "https://irdai.gov.in/health-insurers1",
        "https://bimabharosa.irdai.gov.in/Home/UnclaimedAmount",
    ]


def test_product9_screening_forbids_web_search_and_raw_selector_context() -> None:
    protocol = _load()
    traversal = protocol["source_traversal"]
    boundary = protocol["selection_information_boundary"]
    assert traversal["general_web_search_after_protocol_lock"] is False
    assert traversal["search_result_snippets_available_to_selector"] is False
    assert traversal["fallback_to_search_engine_if_direct_traversal_fails"] is False
    assert boundary["selector_input_contract"] == "blind_preselection_product_metadata_v1"
    assert boundary["selector_may_receive_raw_product_signal_output"] is False
    assert boundary["selector_may_receive_raw_sections_or_page_text"] is False
    assert boundary["selector_may_receive_semantic_bucket_presence_or_counts"] is False


def test_product9_only_retries_clean_currentness_insufficient_product8_insurers() -> None:
    eligibility = _load()["prior_experiment_eligibility"]
    assert eligibility["eligible_product8_statuses_for_product9_retry"] == [
        "EXCLUDED_METADATA_CURRENTNESS_INSUFFICIENT"
    ]
    assert "EXCLUDED_PRODUCT8_PRESELECTION_CONTAMINATION" in eligibility["ineligible_product8_statuses"]
    assert "EXCLUDED_PRIOR_TARGET_CONCEPT_CONTAMINATION" in eligibility["ineligible_product8_statuses"]
    assert eligibility["product8_history_is_modified"] is False
    assert eligibility["product8_quarantines_are_reversed"] is False


def test_product9_selection_is_deterministic_and_requires_projection_hash() -> None:
    protocol = _load()
    selection = protocol["selection_protocol"]
    boundary = protocol["selection_information_boundary"]
    assert selection["insurer_sort"] == "normalized insurer legal/display name lower-case ASCII ascending"
    assert "two distinct official metadata projections" in selection["currentness_corroboration"]
    assert selection["semantic_fit_may_affect_selection"] is False
    assert selection["selection_override_authorized"] is False
    assert selection["selection_record_must_merge_before_product_document_acquisition"] is True
    assert boundary["projection_hash_must_be_recorded_in_selection_ledger"] is True


def test_product9_semantic_review_waits_for_v42_currentness_gate() -> None:
    sequence = _load()["post_selection_sequence"]
    assert sequence["target_clause_reads_before_positive_currentness_eligibility"] == 0
    assert sequence["post_selection_product_or_version_substitution_authorized"] is False
    assert sequence["if_acquisition_or_currentness_fails"] == "CLOSE_PRODUCT9_UNSCORED"
    assert sequence["semantic_pass_may_override_currentness_failure"] is False
    assert any("CurrentProductRepeatabilityEvidenceEligibility" in step for step in sequence["required"])


def test_product9_primary_metrics_preserve_blindness_and_motor_gate() -> None:
    protocol = _load()
    metrics = protocol["primary_metrics"]
    motor = protocol["motor_readiness_gate"]
    assert metrics["broad_search_engine_queries_during_screening"] == 0
    assert metrics["selector_raw_page_or_product_signal_reads"] == 0
    assert metrics["selector_semantic_bucket_reads"] == 0
    assert metrics["selection_projection_hashes_missing"] == 0
    assert metrics["preselection_target_clause_reads"] == 0
    assert motor["product9_unscored_cannot_satisfy_gate"] is True
