import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v4_product7.json"


def _protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_product7_protocol_is_locked_before_selection():
    protocol = _protocol()
    assert protocol["schema_version"] == "4.0"
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT7_SELECTION"
    assert protocol["experiment"]["product_number"] == 7
    assert protocol["experiment"]["product_selected"] is False
    assert protocol["experiment"]["target_concepts"] == ["copayment", "waiting_period"]


def test_acko_and_prior_cold_start_insurers_are_excluded():
    exclusions = _protocol()["contamination_exclusions"]
    assert exclusions["insurers_excluded_due_to_product6_preselection_exposure"] == ["ACKO General Insurance Limited"]
    prior = "\n".join(exclusions["insurers_excluded_due_to_prior_cold_start_use"])
    for insurer in ("Star Health", "Bajaj", "HDFC ERGO", "Tata AIG", "Niva Bupa"):
        assert insurer in prior
    assert exclusions["exclusion_is_permanent_for_product7"] is True


def test_preselection_firewall_prohibits_clause_bearing_documents():
    firewall = _protocol()["preselection_metadata_firewall"]
    prohibited = set(firewall["prohibited_source_classes_before_selection_record_merge"])
    for source_class in (
        "policy wording",
        "prospectus",
        "customer information sheet (CIS)",
        "proposal form",
        "brochure containing benefit mechanics",
    ):
        assert source_class in prohibited
    assert firewall["product_document_opening_before_selection_record_merge"] is False
    assert firewall["target_clause_read_tolerance"] == 0
    assert "immediately stop screening that insurer" in firewall["contamination_rule"]


def test_preselection_allowed_sources_are_metadata_only():
    allowed = "\n".join(_protocol()["preselection_metadata_firewall"]["allowed_source_classes"])
    assert "insurer list" in allowed
    assert "non-policy HTML product catalogue" in allowed
    assert "product/UIN table" in allowed
    assert "repository exact-name/UIN search" in allowed
    assert "policy wording" not in allowed


def test_product7_selection_has_no_override_or_semantic_fit():
    selection = _protocol()["selection_protocol"]
    assert selection["selection_override_authorized"] is False
    assert selection["semantic_fit_may_affect_selection"] is False
    assert selection["stopping_rule"] == "Stop at the first eligible uncontaminated insurer."
    assert "UIN/product identifier ascending" in selection["product_tie_break"]


def test_product7_primary_metrics_begin_zero_and_motor_gate_is_strict():
    protocol = _protocol()
    assert all(value == 0 for value in protocol["primary_metrics"].values())
    gate = protocol["motor_readiness_gate"]
    assert gate["authorized_outcomes"] == ["STRONG_REPEATABILITY_PROVEN", "MINIMUM_REPEATABILITY_PROVEN"]
    assert gate["product6_abort_cannot_satisfy_gate"] is True
    assert gate["post_gap_corrective_validation_cannot_satisfy_gate"] is True


def test_selection_record_must_merge_before_selected_product_document_opening():
    required = "\n".join(_protocol()["required_artifacts_before_semantic_review"])
    assert "merged Product #7 selection record" in required
    assert "preselection_target_clause_reads equals zero" in required
    assert "no prohibited product document was opened" in required
