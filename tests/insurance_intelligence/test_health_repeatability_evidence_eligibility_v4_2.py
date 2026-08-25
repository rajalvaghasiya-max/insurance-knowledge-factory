import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AMENDMENT = ROOT / "docs/architecture/health_post_hc1_repeatability_evidence_eligibility_v4_2.json"
INVALIDATION = ROOT / "docs/architecture/health_product7_currentness_selection_invalidation_2026-08-25.json"
SELECTION = ROOT / "docs/architecture/health_product7_selection_icici_lombard_arogya_sanjeevani_2026-08-24.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v4_2_separates_semantic_certification_from_current_product_scoring() -> None:
    amendment = _load(AMENDMENT)
    boundary = amendment["semantic_certification_boundary"]
    assert amendment["schema_version"] == "4.2"
    assert amendment["amendment_status"] == "LOCKED_BEFORE_NEXT_COLD_START_EXPERIMENT"
    assert boundary["semantic_certification_may_pass_for_historical_versions"] is True
    assert boundary["semantic_certification_does_not_establish_currentness"] is True
    assert boundary["semantic_certification_does_not_by_itself_authorize_current_product_scoring"] is True
    assert boundary["historical_reasoning_use_cases_remain_supported"] is True


def test_current_product_scoring_requires_governed_exact_version_eligibility() -> None:
    gate = _load(AMENDMENT)["current_product_scoring_gate"]
    requirements = set(gate["all_conditions_required"])
    assert "document version id matches exactly" in requirements
    assert "document content SHA-256 matches exactly" in requirements
    assert "document role matches exactly" in requirements
    assert "document identity resolution status is resolved" in requirements
    assert "temporal_status is current_observed_reviewed" in requirements
    assert gate["fail_closed_on_missing_or_ambiguous_exact_binding"] is True
    assert gate["semantic_pass_cannot_override_gate_failure"] is True


def test_product7_selection_is_preserved_but_experiment_is_unscored() -> None:
    selection = _load(SELECTION)
    closure = _load(INVALIDATION)
    assert selection["selected_product"]["uin"] == "ICIHLIP20178V011920"
    assert closure["selected_product"]["selected_uin"] == selection["selected_product"]["uin"]
    decision = closure["experiment_decision"]
    assert closure["record_status"] == "IMMUTABLE_EXPERIMENT_CLOSURE"
    assert decision["status"] == "CURRENTNESS_SELECTION_INVALIDATED"
    assert decision["scoring_status"] == "UNSCORED"
    assert decision["selection_record_remains_immutable"] is True
    assert decision["substitute_v02_into_product7_authorized"] is False
    assert decision["retroactive_rescoring_authorized"] is False
    assert decision["motor_gate_authorized"] is False


def test_product7_invalidation_is_currentness_not_semantic_falsification() -> None:
    closure = _load(INVALIDATION)
    consequence = closure["architecture_consequence"]
    observation = closure["post_selection_currentness_observation"]
    observed_uins = {item["observed_uin"] for item in observation["observations"]}
    assert observed_uins == {"ICIHLIP20178V011920", "ICIHLIP25041V022425"}
    assert observation["governed_currentness_overlay_for_selected_uin_present"] is False
    assert observation["selected_uin_current_observed_reviewed"] is False
    assert consequence["semantic_certification_is_not_invalidated_by_this_record"] is True
    assert consequence["future_current_product_repeatability_scoring_requires_v4_2_evidence_eligibility_gate"] is True
