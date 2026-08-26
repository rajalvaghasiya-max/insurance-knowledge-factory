import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREREG = ROOT / "docs" / "architecture" / "health_governed_eligible_universe_preregistration_c5_29_2026-08-26.json"
AUTH = ROOT / "docs" / "architecture" / "health_eligible_universe_construction_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_29_is_locked_before_universe_construction():
    data = _load(PREREG)
    assert data["record_status"] == "LOCKED_BEFORE_ELIGIBLE_UNIVERSE_CONSTRUCTION"
    assert data["eligible_universe_construction_authorized"] is False
    assert data["product14_selection_authorized"] is False
    assert data["target_clause_reads_authorized"] is False


def test_c5_29_reuses_exact_four_insurer_neutral_pool():
    data = _load(PREREG)
    assert data["candidate_insurer_pool"]["insurers"] == [
        "Cholamandalam MS General Insurance Company Limited",
        "Magma General Insurance Limited",
        "Navi General Insurance Limited",
        "Shriram General Insurance Company Limited",
    ]
    assert data["freeze"]["candidate_insurer_pool_change_allowed_after_merge"] is False


def test_c5_29_requires_full_pool_adjudication_and_no_stop_at_first():
    data = _load(PREREG)
    assert data["exhaustive_adjudication"]["no_unadjudicated_candidate_permitted_at_freeze"] is True
    assert data["exhaustive_adjudication"]["no_stop_at_first_behavior"] is True
    assert data["exhaustive_adjudication"]["adjudication_ledger_must_include_ineligible_candidates"] is True


def test_c5_29_freezes_non_target_eligibility_predicate():
    data = _load(PREREG)
    predicates = {item["predicate_id"] for item in data["eligibility_predicate"]["required_predicates"]}
    assert predicates == {
        "domain",
        "benefit_basis",
        "insurance_object_type",
        "issuer_authority",
        "coverage_arrangement",
        "current_offering",
        "exact_identity",
    }
    assert data["eligibility_predicate"]["target_concepts_are_not_predicates"] is True
    assert data["eligibility_predicate"]["semantic_fit_is_not_a_predicate"] is True


def test_c5_29_selector_view_is_opaque_and_semantically_blind():
    data = _load(PREREG)
    assert data["opaque_identifier_rule"]["format"] == "eligible_sha256:<64-lowercase-hex>"
    assert data["opaque_identifier_rule"]["selector_may_reverse_map_before_selection"] is False
    forbidden = set(data["eligible_universe_artifact_contract"]["artifact_contents_forbidden"])
    assert {"copayment indicators", "waiting-period indicators", "semantic-fit score"} <= forbidden
    assert data["future_product14_selection_rule"]["authorized_now"] is False


def test_c5_29_preserves_c5_24_runtime_firewall_and_fail_closed_behavior():
    data = _load(PREREG)
    contract = data["certification_evidence_contract"]
    assert contract["certification_stage_is_not_runtime_selector"] is True
    assert contract["c5_24_runtime_source_firewall_remains_unchanged"] is True
    assert contract["unknown_or_conflicting_required_predicate"] == "INELIGIBLE_FAIL_CLOSED"


def test_c5_29_next_authorization_is_construction_only():
    auth = _load(AUTH)
    assert auth["record_status"] == "PENDING_C5_29_GREEN_MERGE"
    assert auth["authorized_next_action"] == "HEALTH_GOVERNED_ELIGIBLE_UNIVERSE_CONSTRUCTION_AND_CERTIFICATION_ONLY"
    assert auth["product14_selection_authorized"] is False
    assert auth["target_clause_reads_authorized"] is False
    assert auth["runtime_change_authorized"] is False
    assert auth["motor_authorized"] is False
