import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v3.json"
BASELINE = "f05ca07283f53f2882ed5da3ca27875ba7253318"


def _protocol():
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_protocol_is_locked_before_product6_selection():
    protocol = _protocol()
    assert protocol["schema_version"] == "3.0"
    assert protocol["protocol_status"] == "LOCKED_BEFORE_PRODUCT6_SELECTION"
    assert protocol["baseline_commit"] == BASELINE
    assert protocol["retroactive_rescoring_authorized"] is False
    assert protocol["experiment"]["product_number"] == 6
    assert protocol["experiment"]["product_selected"] is False
    assert protocol["experiment"]["target_concepts"] == ["copayment", "waiting_period"]


def test_selection_is_metadata_only_and_deterministic():
    selection = _protocol()["selection_protocol"]
    assert selection["selection_must_occur_after_protocol_merge"] is True
    assert selection["selection_override_authorized"] is False
    assert "copayment clauses" in selection["target_clause_content_must_not_be_read_before_selection"]
    assert "waiting-period clauses" in selection["target_clause_content_must_not_be_read_before_selection"]
    assert selection["deterministic_tie_break"] == [
        "Normalize insurer legal/display name to lower-case ASCII for sorting.",
        "Sort eligible candidates by normalized insurer name ascending.",
        "Within an insurer, sort by normalized UIN/product identifier ascending.",
        "Select the first candidate in that ordered list.",
    ]
    allowed = set(selection["selection_evidence_may_use_only_metadata"])
    assert allowed == {
        "insurer identity",
        "product name",
        "UIN or regulator/product identifier",
        "retail Health indemnity classification",
        "official current policy-wording availability",
        "repository exposure search result",
    }


def test_prior_cold_start_insurers_are_excluded_before_clause_review():
    rules = "\n".join(_protocol()["selection_protocol"]["eligible_product_rules"])
    for insurer in ("Star Health", "Bajaj", "HDFC ERGO", "Tata AIG", "Niva Bupa"):
        assert insurer in rules
    assert "official insurer or regulator source" in rules.lower()
    assert "exact UIN/product identifier" in rules


def test_runtime_and_semantic_surfaces_are_frozen_for_initial_attempt():
    freeze = _protocol()["freeze"]
    assert freeze["runtime_change_allowed_during_initial_attempt"] is False
    assert freeze["new_semantic_or_spec_shape_allowed_during_initial_attempt"] is False
    assert freeze["decision_logic_in_config_is_failure"] is True
    assert freeze["baseline_commit_must_remain_the_scoring_reference"] is True
    assert set(freeze["frozen_surfaces"]) == {
        "insurance_intelligence/contracts/",
        "insurance_intelligence/reasoning/",
        "insurance_intelligence/benefits/",
        "insurance_intelligence/rule_certification/",
        "factory_core/canonical/",
        "knowledge_domains/health/",
    }


def test_primary_repeatability_metrics_begin_at_zero():
    metrics = _protocol()["primary_metrics"]
    assert metrics
    assert all(value == 0 for value in metrics.values())
    assert metrics["selection_rule_overrides"] == 0
    assert metrics["preselection_target_clause_reads"] == 0
    assert metrics["new_declarative_schema_shapes"] == 0


def test_motor_gate_requires_new_neutral_repeatability_proof():
    protocol = _protocol()
    motor_gate = protocol["motor_readiness_gate"]
    assert "STRONG_REPEATABILITY_PROVEN" in motor_gate["motor_readiness_review_may_begin_only_if"]
    assert "MINIMUM_REPEATABILITY_PROVEN" in motor_gate["motor_readiness_review_may_begin_only_if"]
    assert "post-gap corrective validation" in motor_gate["if_not_proven"]
    assert "SELECTION_INCONCLUSIVE" in protocol["success_bar"]


def test_required_artifacts_force_selection_commit_before_semantic_review():
    required = _protocol()["required_artifacts_before_semantic_review"]
    assert any("committed Product #6 selection record" in item for item in required)
    assert any("preselection_target_clause_reads equals zero" in item for item in required)
    assert any("repository exposure check at the baseline commit" in item for item in required)
