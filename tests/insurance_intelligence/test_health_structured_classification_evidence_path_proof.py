import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / "docs/architecture/health_structured_classification_evidence_path_proof_2026-08-26.json"
AUTH = ROOT / "docs/architecture/health_bounded_metadata_source_survey_authorization_v1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_25_is_governance_only_and_product14_remains_blocked():
    proof = _load(PROOF)
    assert proof["milestone"] == "C5.25"
    assert proof["runtime_changed"] is False
    assert proof["product14_authorized"] is False
    assert proof["implementation_authorized"] is False
    assert proof["target_clause_reads_authorized"] is False
    assert proof["motor_authorized"] is False


def test_object_type_is_metadata_establishable_but_not_by_uin_shape():
    finding = _load(PROOF)["predicate_findings"]["insurance_object_type"]
    assert finding["establishability"] == "REGULATOR_METADATA_ESTABLISHABLE"
    assert finding["uin_shape_sufficient"] is False
    assert finding["fail_closed_on_missing_or_conflict"] is True


def test_benefit_basis_and_coverage_arrangement_are_not_yet_demonstrated():
    findings = _load(PROOF)["predicate_findings"]
    assert findings["benefit_basis"]["establishability"] == "NOT_YET_DEMONSTRATED"
    assert findings["benefit_basis"]["uin_shape_sufficient"] is False
    assert findings["coverage_arrangement"]["establishability"] == "NOT_YET_DEMONSTRATED"


def test_semantic_bearing_documents_remain_outside_preselection():
    boundary = _load(PROOF)["source_boundary"]
    assert "semantic_bearing_filed_product_document_filtered_after_parse" in boundary["forbidden"]
    assert "policy_wording" in boundary["forbidden"]
    assert "prospectus" in boundary["forbidden"]
    assert "customer_information_sheet" in boundary["forbidden"]


def test_no_structural_ceiling_is_claimed_without_positive_proof():
    ceiling = _load(PROOF)["structural_ceiling"]
    assert ceiling["proven"] is False
    assert _load(PROOF)["verdict"] == "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE"


def test_next_authorization_is_only_bounded_metadata_source_survey():
    proof = _load(PROOF)
    auth = _load(AUTH)
    assert proof["next_authorized_action"] == "HEALTH_BOUNDED_METADATA_SOURCE_SURVEY_FOR_BENEFIT_BASIS_AND_COVERAGE_ARRANGEMENT_ONLY"
    assert auth["authorized_next_action"] == proof["next_authorized_action"]
    assert auth["forbidden"]["runtime_change"] is True
    assert auth["forbidden"]["selector_projection_change"] is True
    assert auth["forbidden"]["product14_preregistration"] is True
    assert auth["forbidden"]["product14_execution"] is True


def test_required_outcomes_preserve_closed_incomplete_or_ceiling_distinction():
    outcomes = set(_load(AUTH)["required_outcome"])
    assert outcomes == {
        "BLIND_SELECTION_PREDICATE_CLOSED_AND_ESTABLISHABLE",
        "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE",
        "BLIND_SELECTION_STRUCTURAL_CEILING_PROVEN",
    }
