import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "docs" / "architecture" / "health_blind_selection_predicate_evidence_path_proof_c5_23_2026-08-26.json"
AUTH = ROOT / "docs" / "architecture" / "health_preselection_classification_source_boundary_decision_authorization_v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_23_is_proof_only_and_product14_stays_closed():
    proof = load(PROOF)
    assert proof["authorization"] == "HEALTH_BLIND_SELECTION_PREDICATE_EVIDENCE_PATH_PROOF_ONLY"
    assert proof["runtime_changes"] == 0
    assert proof["selector_projection_changes"] == 0
    assert proof["product14_preregistered"] is False
    assert proof["target_clause_reads"] == 0
    assert proof["motor_authorized"] is False


def test_c5_23_does_not_overclaim_closed_or_structural_ceiling():
    proof = load(PROOF)
    assert proof["verdict"] == "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE"
    for result in proof["predicate_results"]:
        assert result["structural_ceiling_proven"] is False
        assert result["projection_delta_authorized"] is False


def test_benefit_basis_does_not_infer_indemnity_from_uin_or_individual_status():
    proof = load(PROOF)
    benefit_basis = next(item for item in proof["predicate_results"] if item["predicate_id"] == "benefit_basis")
    joined = " ".join(benefit_basis["evidence_findings"])
    assert "not sufficient to prove indemnity" in joined
    assert benefit_basis["establishability_under_blindness"] == "NOT_YET_DEMONSTRATED"


def test_object_type_is_only_metadata_establishable_where_explicit():
    proof = load(PROOF)
    object_type = next(item for item in proof["predicate_results"] if item["predicate_id"] == "insurance_object_type")
    assert object_type["establishability_under_blindness"] == "REGULATOR_METADATA_ESTABLISHABLE_WHERE_EXPLICIT"
    assert any("Main Product/Add-on" in item for item in object_type["evidence_findings"])


def test_coverage_arrangement_remains_not_yet_universally_demonstrated():
    proof = load(PROOF)
    arrangement = next(item for item in proof["predicate_results"] if item["predicate_id"] == "coverage_arrangement")
    assert arrangement["closure_type"] == "EXPERIMENT_STIPULATED"
    assert arrangement["establishability_under_blindness"] == "NOT_YET_DEMONSTRATED"


def test_anti_contamination_remains_adversarial_not_exhaustively_complete():
    proof = load(PROOF)
    anti = proof["anti_contamination"]
    assert anti["closure_model"] == "ADVERSARIAL_INVARIANT"
    assert anti["exhaustive_completeness_claim"] is False


def test_next_action_is_source_boundary_decision_only():
    proof = load(PROOF)
    auth = load(AUTH)
    assert proof["next_action"] == "HEALTH_PRESELECTION_CLASSIFICATION_SOURCE_BOUNDARY_DECISION_ONLY"
    assert auth["authorized_next_action"] == proof["next_action"]
    assert auth["forbidden"]["runtime_change"] is True
    assert auth["forbidden"]["selector_projection_change"] is True
    assert auth["forbidden"]["product14_preregistration"] is True
    assert auth["forbidden"]["target_clause_reads"] is True
    assert auth["forbidden"]["motor"] is True
