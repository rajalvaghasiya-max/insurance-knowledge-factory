import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "docs/architecture/health_product4_repeatability_test_protocol_v1.json"
BASELINE = "bda5eb8721e04f8a78118ca4c4e054a09520a6d4"
FROZEN = {
    "insurance_intelligence/contracts/",
    "insurance_intelligence/reasoning/",
    "insurance_intelligence/benefits/",
    "insurance_intelligence/rule_certification/",
    "factory_core/canonical/",
}
PRIMARY_METRICS = {
    "new_runtime_files",
    "runtime_loc_delta",
    "product_specific_branches_in_generic_runtime",
    "decision_logic_added_in_config_or_fixtures",
    "certified_claims_without_exact_candidate_version_hash_lineage",
    "silent_coercions_of_unsupported_semantics",
}


def _protocol():
    return json.loads(PROTOCOL.read_text(encoding="utf-8"))


def test_protocol_is_preregistered_before_fourth_product_selection() -> None:
    protocol = _protocol()
    assert protocol["protocol_status"] == "PREREGISTERED_BEFORE_PRODUCT_SELECTION"
    assert protocol["baseline"]["commit_sha"] == BASELINE
    assert protocol["experiment"]["product_number"] == 4
    assert protocol["experiment"]["product_selected_at_preregistration"] is False
    assert protocol["experiment"]["target_concepts"] == ["copayment", "waiting_period"]


def test_initial_cold_start_freezes_all_generic_decision_surfaces() -> None:
    freeze = _protocol()["initial_cold_start_freeze"]
    assert freeze["runtime_change_allowed"] is False
    assert set(freeze["frozen_surfaces"]) == FROZEN
    assert freeze["decision_logic_in_config_is_failure"] is True
    decision_logic = set(freeze["decision_logic_definition"])
    assert "product-specific computation" in decision_logic
    assert "product-specific branching" in decision_logic
    assert "product-specific precedence resolution" in decision_logic
    assert "an executable decision table that substitutes for generic runtime behavior" in decision_logic


def test_classification_rubric_is_locked_and_non_overlapping_on_decision_logic() -> None:
    rubric = _protocol()["classification_rubric"]
    assert set(rubric) == {"REUSE", "CONFIG_SPEC", "REPRESENTATION_GAP", "KNOWLEDGE_GAP"}
    assert "Existing generic contract" in rubric["REUSE"]["rule"]
    assert "no computation, branching, precedence logic" in rubric["CONFIG_SPEC"]["rule"]
    assert rubric["CONFIG_SPEC"]["costed_as_manual_manufacturing_work"] is True
    assert "Certification must block" in rubric["REPRESENTATION_GAP"]["rule"]
    assert "Code must not compensate" in rubric["KNOWLEDGE_GAP"]["rule"]


def test_primary_metrics_include_runtime_and_runtime_in_exile_guards() -> None:
    metrics = _protocol()["primary_metrics"]
    assert set(metrics) == PRIMARY_METRICS
    assert all(metric["target"] == 0 for metric in metrics.values())


def test_success_bar_requires_actual_reuse_not_only_new_specs() -> None:
    bar = _protocol()["precommitted_success_bar"]
    strong = set(bar["STRONG_REPEATABILITY_PROVEN"]["requirements"])
    minimum = set(bar["MINIMUM_REPEATABILITY_PROVEN"]["requirements"])
    assert "copayment classification is REUSE" in strong
    assert "waiting_period classification is REUSE" in strong
    assert "at least one of the two target concepts is classified REUSE" in minimum
    assert "both target concepts are classified only as REUSE or CONFIG_SPEC" in minimum
    assert "no target concept is REPRESENTATION_GAP" in minimum
    assert "both target concepts are CONFIG_SPEC with zero REUSE" in bar["REPEATABILITY_NOT_PROVEN"]["trigger"]


def test_gap_handling_cannot_be_gamed_into_success() -> None:
    protocol = _protocol()
    rules = protocol["anti_gaming_rules"]
    assert any("decision logic" in rule and "failure" in rule for rule in rules)
    assert any("representation gap must be recorded before" in rule.lower() for rule in rules)
    assert any("No unsupported concept is required or desired" in rule for rule in rules)
    governance = protocol["post_test_governance"]
    assert governance["runtime_extension_after_gap_recording_allowed"] is True
    assert governance["runtime_extension_counts_as_initial_repeatability_success"] is False
