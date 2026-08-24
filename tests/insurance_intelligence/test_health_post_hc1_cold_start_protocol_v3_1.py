import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AMENDMENT_PATH = ROOT / "docs/architecture/health_post_hc1_neutral_cold_start_protocol_v3_1_amendment.json"


def _amendment():
    return json.loads(AMENDMENT_PATH.read_text(encoding="utf-8"))


def test_amendment_is_locked_before_product6_selection_and_semantic_review():
    amendment = _amendment()
    assert amendment["schema_version"] == "3.1"
    assert amendment["amendment_status"] == "LOCKED_BEFORE_PRODUCT6_SELECTION"
    assert amendment["product6_selected_before_amendment"] is False
    assert amendment["target_clause_review_before_amendment"] is False
    assert amendment["semantic_fit_used_to_design_amendment"] is False


def test_stopping_rule_preserves_insurer_first_determinism():
    rule = _amendment()["selection_rule_replacement"]
    assert "IRDAI insurer list" in rule["insurer_universe"]
    assert "ascending order" in rule["insurer_order"]
    assert "first insurer" in rule["stopping_rule"]
    assert "Later insurers are not enumerated" in rule["stopping_rule"]
    assert "every product from the first eligible insurer" in rule["selected_insurer_product_enumeration"]
    assert "UIN/product identifier ascending" in rule["product_tie_break"]
    assert rule["selection_override_authorized"] is False


def test_prior_cold_start_insurers_remain_excluded():
    excluded = "\n".join(_amendment()["selection_rule_replacement"]["prior_cold_start_exclusions"])
    for insurer in ("Star Health", "Bajaj", "HDFC ERGO", "Tata AIG", "Niva Bupa"):
        assert insurer in excluded


def test_amendment_does_not_weaken_frozen_experiment_boundaries():
    unchanged = "\n".join(_amendment()["unchanged_v3_rules"])
    assert "target-clause content must not be reviewed" in unchanged
    assert "runtime and semantic/spec surfaces remain frozen" in unchanged
    assert "copayment and waiting_period" in unchanged
    assert "Product #5 scoring remains immutable" in unchanged
    assert "Motor readiness remains gated" in unchanged


def test_amendment_is_outcome_equivalent_not_semantic_selection():
    governance = _amendment()["governance"]
    assert governance["amendment_changes_candidate_outcome_ordering"] is False
    assert governance["amendment_uses_product_semantics"] is False
    assert governance["retroactive_product_selection_authorized"] is False
