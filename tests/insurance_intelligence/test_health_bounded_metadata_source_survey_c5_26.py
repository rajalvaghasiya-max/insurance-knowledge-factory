import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SURVEY = ROOT / "docs/architecture/health_bounded_metadata_source_survey_c5_26_2026-08-26.json"
AUTH = ROOT / "docs/architecture/health_benefit_basis_blind_safe_evidence_path_decision_authorization_v1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_26_survey_verdict_remains_incomplete():
    data = _load(SURVEY)
    assert data["verdict"] == "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE"
    assert data["base_merge_sha"] == "fc32f4bafbba0fcbb210d6208a67f75a40c1f76e"


def test_coverage_arrangement_is_metadata_establishable_in_principle_only():
    data = _load(SURVEY)
    finding = data["findings"]["coverage_arrangement"]
    assert finding["status"] == "METADATA_ESTABLISHABLE_IN_PRINCIPLE"
    assert "universal regulator register field is not demonstrated" in finding["caveat"]


def test_benefit_basis_remains_not_yet_demonstrated():
    data = _load(SURVEY)
    finding = data["findings"]["benefit_basis"]
    assert finding["status"] == "NOT_YET_DEMONSTRATED"
    assert "no universally bounded structured regulator/insurer metadata surface" in finding["blocker"]


def test_semantic_bearing_documents_remain_forbidden_preselection_sources():
    data = _load(SURVEY)
    forbidden = set(data["source_boundary"]["forbidden"])
    assert {"policy_wording", "prospectus", "customer_information_sheet", "cis"} <= forbidden
    assert "semantic-bearing filed product document filtered after parsing" in forbidden


def test_c5_26_does_not_claim_structural_ceiling():
    data = _load(SURVEY)
    conclusion = data["architecture_conclusion"]
    assert "No structural ceiling is proven" in conclusion
    assert "benefit basis remains the unresolved" in conclusion


def test_next_authorization_is_benefit_basis_decision_only():
    data = _load(AUTH)
    assert data["authorized_next_action"] == "HEALTH_BENEFIT_BASIS_BLIND_SAFE_EVIDENCE_PATH_DECISION_ONLY"
    assert data["scope"]["predicate"] == "benefit_basis"


def test_product14_runtime_semantics_and_motor_remain_closed():
    data = _load(AUTH)
    forbidden = data["forbidden"]
    assert forbidden["runtime_change"] is True
    assert forbidden["selector_projection_change"] is True
    assert forbidden["product14_preregistration"] is True
    assert forbidden["product14_execution"] is True
    assert forbidden["target_clause_reads"] is True
    assert forbidden["semantic_fit_selection"] is True
    assert forbidden["motor"] is True
