import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = ROOT / "docs/architecture/health_product7_pre_certification_frozen_fit_2026-08-25.json"


def _checkpoint():
    return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))


def test_checkpoint_preserves_frozen_baseline_and_pending_verdict():
    checkpoint = _checkpoint()
    governance = checkpoint["governance"]
    boundary = checkpoint["pre_certification_result_boundary"]

    assert governance["frozen_scoring_baseline_commit"] == "f05ca07283f53f2882ed5da3ca27875ba7253318"
    assert governance["final_repeatability_verdict_assigned"] is False
    assert boundary["repeatability_verdict"] == "PENDING_EXACT_SOURCE_LINEAGE"
    assert boundary["motor_gate"] == "CLOSED"


def test_exact_binary_lineage_is_required_before_certification():
    source = _checkpoint()["source_review"]

    assert source["authoritative_semantic_text_reviewed"] is True
    assert source["exact_source_binary_acquired_into_governed_repository"] is False
    assert source["source_content_sha256"] is None
    assert source["candidate_text_sha256_values"] is None
    assert source["canonical_source_registration_complete"] is False
    assert source["certification_authorized"] is False
    assert "No substitute text hash" in source["lineage_blocker_reason"]


def test_policy_wide_fixed_copayment_is_not_coerced_into_conditional_reuse():
    copayment = _checkpoint()["frozen_fit_review"]["copayment"]

    assert copayment["baseline_fit_status"] == "REPRESENTATION_GAP_INDICATED"
    assert copayment["not_final_classification"] is True
    assert copayment["observed_shape"]["rate_percentage"] == 5
    assert copayment["observed_shape"]["documented_trigger_condition"] is None
    reasons = "\n".join(copayment["baseline_findings"])
    assert "each and every claim is applicability scope, not a trigger condition" in reasons
    assert "coercing policy-wide applicability into a trigger is prohibited" in reasons


def test_waiting_period_scalar_variants_reuse_existing_frozen_shape_but_precedence_does_not():
    variants = {
        item["variant_id"]: item
        for item in _checkpoint()["frozen_fit_review"]["waiting_period_variants"]
    }

    for variant_id in (
        "PED_FIXED_48_MONTHS",
        "INITIAL_FIXED_30_DAYS",
        "SPECIFIC_DISEASE_24_MONTHS",
        "SPECIFIC_DISEASE_48_MONTHS",
    ):
        assert variants[variant_id]["baseline_fit_status"] == "REUSE_INDICATED"
        assert variants[variant_id]["not_final_classification"] is True

    precedence = variants["PED_VS_SPECIFIC_LONGER_WAIT_PRECEDENCE"]
    assert precedence["baseline_fit_status"] == "REPRESENTATION_GAP_INDICATED"
    assert precedence["not_final_classification"] is True
    assert "longer of the applicable waiting periods applies" in precedence["observed_relationship"]


def test_checkpoint_does_not_change_runtime_or_smuggle_decision_logic():
    budget = _checkpoint()["checkpoint_change_budget"]
    assert all(value == 0 for value in budget.values())
