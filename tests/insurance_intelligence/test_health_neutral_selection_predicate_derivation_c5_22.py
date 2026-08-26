import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs" / "architecture" / "health_neutral_selection_predicate_derivation_c5_22_2026-08-26.json"
AUTH = ROOT / "docs" / "architecture" / "health_blind_selection_predicate_evidence_path_proof_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_22_uses_three_distinct_closure_models() -> None:
    review = _load(REVIEW)
    models = review["closure_models"]
    assert models["regulatory_taxonomy"]["closure_type"] == "REGULATORY_DERIVED"
    assert models["regulatory_taxonomy"]["completeness_claim_allowed"] is True
    assert models["experiment_population"]["closure_type"] == "EXPERIMENT_STIPULATED"
    assert models["experiment_population"]["completeness_claim_allowed"] is True
    assert models["cold_start_integrity"]["closure_type"] == "ADVERSARIAL_INVARIANT"
    assert models["cold_start_integrity"]["completeness_claim_allowed"] is False


def test_c5_22_scores_every_regulatory_predicate_for_blind_establishability() -> None:
    review = _load(REVIEW)
    allowed = set(review["establishability_scale"])
    predicates = review["authoritative_regulatory_findings"]
    assert predicates
    assert {item["predicate_id"] for item in predicates} >= {
        "health_business_scope",
        "issuer_authority_for_indemnity_health",
        "benefit_basis",
        "distribution_scope",
        "insurance_object_type",
        "coverage_arrangement",
    }
    for item in predicates:
        assert item["establishability_under_blindness"] in allowed


def test_c5_22_does_not_claim_indemnity_or_object_type_is_already_closed_operationally() -> None:
    review = _load(REVIEW)
    by_id = {item["predicate_id"]: item for item in review["authoritative_regulatory_findings"]}
    assert by_id["benefit_basis"]["establishability_under_blindness"] == "NOT_YET_DEMONSTRATED"
    assert by_id["insurance_object_type"]["establishability_under_blindness"] == "NOT_YET_DEMONSTRATED"
    assert by_id["coverage_arrangement"]["establishability_under_blindness"] == "NOT_YET_DEMONSTRATED"
    assert review["c5_22_verdict"] == "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE"


def test_c5_22_splits_failure_routes_by_layer() -> None:
    review = _load(REVIEW)
    outcomes = review["closure_outcomes"]
    assert "REGULATORY_TAXONOMY_COMPLETENESS_FALSIFIED" in outcomes
    assert "EXPERIMENT_POPULATION_DEFINITION_INCONSISTENT" in outcomes
    assert "ANTI_CONTAMINATION_BOUNDARY_FALSIFIED" in outcomes
    assert "FAIL_CLOSED_PREDICATE_EVIDENCE_PATH" in outcomes
    assert "BLIND_SELECTION_STRUCTURAL_CEILING_PROVEN" in outcomes


def test_c5_22_treats_anti_contamination_as_adversarial_assurance_not_enumerated_completeness() -> None:
    review = _load(REVIEW)
    integrity = review["cold_start_integrity_invariants"]
    assert integrity["completeness_claim"] is False
    assert integrity["assurance_claim_allowed"] == "ADVERSARIAL_ASSURANCE_PASSED_FOR_FROZEN_THREAT_MODEL"
    assert integrity["assurance_claim_forbidden"] == "ALL_CONTAMINATION_PATHS_EXHAUSTIVELY_PROVEN_IMPOSSIBLE"


def test_c5_22_reuse_audit_calls_bridge_partial_not_wholly_absent() -> None:
    review = _load(REVIEW)
    reuse = review["reuse_audit"]
    assert reuse["prior_protocol_v3_already_contains_broad_population_prose"] is True
    assert reuse["indemnity_concept_exists_in_health_knowledge"] is True
    assert reuse["existing_blind_v2_identity_projection_reusable"] is True
    assert reuse["existing_identity_currentness_companion_projection_reusable"] is True
    assert reuse["closed_regulatory_taxonomy_to_selector_evidence_bridge_already_exists"] is False
    assert "partial rather than absent" in reuse["finding"].lower()


def test_c5_22_blocks_product14_and_runtime_until_evidence_paths_are_proven() -> None:
    review = _load(REVIEW)
    permissions = review["permissions"]
    assert permissions["may_change_runtime"] is False
    assert permissions["may_change_selector_projection"] is False
    assert permissions["may_preregister_product14"] is False
    assert permissions["may_run_product14"] is False
    assert permissions["may_read_target_clauses"] is False
    assert permissions["may_start_motor"] is False
    assert review["next_authorized_action"] == "HEALTH_BLIND_SELECTION_PREDICATE_EVIDENCE_PATH_PROOF_ONLY"


def test_follow_on_authorization_is_proof_only_and_keeps_product14_closed() -> None:
    auth = _load(AUTH)
    assert auth["record_status"] == "EFFECTIVE_ONLY_AFTER_C5_22_REVIEW_MERGES_GREEN"
    assert auth["authorized_next_action"] == "HEALTH_BLIND_SELECTION_PREDICATE_EVIDENCE_PATH_PROOF_ONLY"
    assert set(auth["scope"]["unresolved_predicates"]) == {
        "benefit_basis",
        "insurance_object_type",
        "coverage_arrangement",
    }
    forbidden = auth["forbidden"]
    assert forbidden["runtime_change"] is True
    assert forbidden["selector_projection_change"] is True
    assert forbidden["product14_preregistration"] is True
    assert forbidden["product14_execution"] is True
    assert forbidden["target_clause_reads"] is True
    assert forbidden["motor"] is True
