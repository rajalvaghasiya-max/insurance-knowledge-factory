import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AMENDMENT_PATH = ROOT / "docs/architecture/health_post_hc1_repeatability_scoring_amendment_v4_1_product7.json"


def _amendment():
    return json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))


def test_scoring_amendment_is_locked_before_product7_certification():
    amendment = _amendment()
    assert amendment["schema_version"] == "4.1"
    assert amendment["amendment_status"] == "LOCKED_BEFORE_PRODUCT7_CERTIFICATION"
    assert amendment["frozen_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert amendment["product_number"] == 7
    assert amendment["runtime_or_semantic_surface_change_authorized"] is False
    assert amendment["scoring_may_not_be_relaxed_after_certification_begins"] is True


def test_product7_scoring_is_variant_grain_and_does_not_inherit_green():
    rule = _amendment()["variant_grain_rule"]
    variants = {item["variant_id"] for item in rule["required_product7_variant_units"]}
    assert variants == {
        "copayment.policy_wide_fixed_rate",
        "waiting_period.pre_existing_disease",
        "waiting_period.initial",
        "waiting_period.specific_condition_24_month",
        "waiting_period.specific_condition_48_month",
    }
    assert rule["no_variant_green_by_inheritance"] is True
    assert rule["mixed_variant_results_are_valid_experiment_results"] is True
    assert rule["mixed_variant_result_does_not_automatically_authorize_motor_gate"] is True


def test_instance_discriminator_forbids_hidden_decision_logic():
    discriminator = _amendment()["instance_vs_structural_shape_discriminator"]
    instance_conditions = "\n".join(discriminator["INSTANCE"]["all_conditions_required"])
    structural_conditions = "\n".join(discriminator["STRUCTURAL_SHAPE"]["any_condition_sufficient"])
    assert "one-to-one" in instance_conditions
    assert "No new conditional evaluation" in instance_conditions
    assert "binder and certifier validate the intended semantic meaning" in instance_conditions
    assert "selectors, conditionals, precedence, ordering, derived values, fallback logic" in structural_conditions
    assert "previously unsupported interaction" in structural_conditions
    assert "STRUCTURAL_SHAPE" in discriminator["tie_break_rule"]


def test_every_certified_claim_requires_positive_semantic_correctness_check():
    gate = _amendment()["positive_semantic_correctness_gate"]
    metrics = gate["required_positive_metrics"]
    assert gate["required"] is True
    assert gate["scope"] == "every certified Product #7 claim, not a sample"
    assert gate["lineage_is_not_semantic_correctness"] is True
    assert metrics["certified_claims_total"] == "N"
    assert metrics["certified_claims_semantically_checked"] == "N"
    assert metrics["semantic_check_coverage_ratio"] == 1.0
    assert metrics["certified_claims_semantically_correct"] == "N"
    assert metrics["semantic_mismatches_unresolved"] == 0
    assert "blocks REUSE/CONFIG_SPEC" in gate["failure_rule"]


def test_concept_reuse_requires_every_required_variant_to_reuse():
    aggregation = _amendment()["concept_aggregation_rule"]
    assert "every required observed Product #7 variant" in aggregation["REUSE"]
    assert "positive semantic-correctness gate" in aggregation["REUSE"]
    assert "any required observed variant" in aggregation["REPRESENTATION_GAP"]
    assert aggregation["mixed_variant_reporting_required"] is True


def test_mixed_result_is_valid_but_representation_gap_keeps_motor_gate_closed():
    guard = _amendment()["repeatability_verdict_guard"]
    assert guard["parent_success_bar_remains_authoritative_for_motor_gate"] is True
    assert guard["strong_requires_positive_gate"] is True
    assert guard["minimum_requires_positive_gate"] is True
    assert guard["all_parent_primary_metrics_must_still_be_zero"] is True
    assert guard["mixed_variant_result_is_not_a_governance_failure"] is True
    assert guard["representation_gap_keeps_motor_gate_closed_under_parent_protocol"] is True


def test_repository_test_count_is_the_only_number_of_record():
    governance = _amendment()["test_count_governance"]
    assert governance["number_of_record_at_parent_main_commit"] == 2933
    assert governance["number_of_record_commit"] == "84140c5bf111a72ac0979f395d6924138c1d109f"
    assert governance["local_untracked_test_count_is_not_a_repository_baseline"] is True
    assert "Git-controlled commit" in governance["rule"]
