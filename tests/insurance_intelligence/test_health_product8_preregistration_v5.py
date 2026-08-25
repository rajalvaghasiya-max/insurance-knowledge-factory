import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v5_product8.json"


def _load() -> dict:
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_product8_protocol_is_locked_before_selection_with_separate_baselines() -> None:
    protocol = _load()
    assert protocol["schema_version"] == "5.0"
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT8_SELECTION"
    assert protocol["experiment"]["product_number"] == 8
    assert protocol["experiment"]["product_selected"] is False
    assert protocol["semantic_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert protocol["experiment_governance_baseline_commit"] == "05852964d762c3d3fc4048892e457459a4a3b264"
    assert protocol["baseline_separation"]["post_selection_change_to_either_baseline_authorized"] is False


def test_product8_excludes_prior_cold_start_and_contaminated_insurers() -> None:
    exclusions = _load()["contamination_exclusions"]
    prior = set(exclusions["insurers_excluded_due_to_prior_cold_start_use"])
    contaminated = set(exclusions["insurers_excluded_due_to_prior_target_concept_preselection_exposure"])
    assert "ICICI Lombard General Insurance Company Limited" in prior
    assert "ACKO General Insurance Limited" in contaminated
    assert "Aditya Birla Health Insurance Co. Ltd." in contaminated
    assert exclusions["exclusions_are_permanent_for_product8"] is True


def test_preselection_currentness_requires_exact_corroborated_uin_without_product_documents() -> None:
    protocol = _load()
    firewall = protocol["preselection_currentness_firewall"]
    metadata = protocol["preselection_metadata_firewall"]
    assert firewall["exact_uin_agreement_required"] is True
    assert firewall["conflicting_uin_or_version_signals"] == "EXCLUDE_CANDIDATE_CURRENTNESS_UNRESOLVED"
    assert firewall["opening_product_documents_to_resolve_preselection_currentness"] is False
    assert firewall["currentness_inference_from_product_name_only"] is False
    assert firewall["currentness_inference_from_non_archived_label_alone"] is False
    assert metadata["product_document_opening_before_selection_record_merge"] is False
    assert metadata["target_clause_read_tolerance"] == 0
    assert "rate chart or premium chart PDF" in metadata["prohibited_source_classes_before_selection_record_merge"]


def test_semantic_review_is_blocked_until_exact_governed_currentness_and_v42_gate() -> None:
    gate = _load()["post_selection_currentness_gate_before_semantic_review"]
    sequence = gate["required_sequence"]
    assert "register immutable source bytes and SHA-256" in sequence
    assert "establish reviewed document identity/currentness through document_identity_resolution_overlay_v1" in sequence
    assert any("CurrentProductRepeatabilityEvidenceEligibility" in step for step in sequence)
    assert sequence[-1] == "only then permit reading copayment or waiting-period target clauses"
    assert gate["semantic_target_clause_reads_before_currentness_resolution"] == 0
    assert gate["substitute_another_version_into_product8_after_selection"] is False
    assert gate["substitute_another_product_into_product8_after_selection"] is False
    assert gate["semantic_certification_pass_may_override_currentness_failure"] is False


def test_product8_primary_metrics_include_currentness_and_no_substitution_guards() -> None:
    metrics = _load()["primary_metrics"]
    assert metrics["current_product_claims_scored_without_v4_2_evidence_eligibility"] == 0
    assert metrics["semantic_target_clause_reads_before_currentness_resolution"] == 0
    assert metrics["post_selection_product_or_version_substitutions"] == 0
    assert metrics["currentness_metadata_conflicts_ignored"] == 0
    assert metrics["preselection_target_clause_reads"] == 0


def test_unscored_operational_closure_is_not_a_semantic_result() -> None:
    protocol = _load()
    rubric = protocol["classification_rubric"]
    success = protocol["success_bar"]
    motor = protocol["motor_readiness_gate"]
    assert "operational experiment failure/closure, not a semantic classification" in rubric["UNSCORABLE_CURRENTNESS_OR_ACQUISITION"]
    assert "do not replace the product/version or infer a semantic outcome" in success["EXPERIMENT_UNSCORED"]
    assert motor["product8_unscored_currentness_or_acquisition_closure_cannot_satisfy_gate"] is True
