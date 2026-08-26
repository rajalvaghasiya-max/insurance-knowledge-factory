import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/architecture/health_preselection_classification_source_boundary_decision_2026-08-26.json"
AUTH = ROOT / "docs/architecture/health_preselection_structured_classification_evidence_path_authorization_v1.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_24_pins_exact_c5_23_merge_baseline():
    data = _load(DECISION)
    assert data["baseline_commit"] == "005e9707cb183c949cdbb48e123cfaa2dc0affbd"
    assert data["record_status"] == "FROZEN_PENDING_MERGE"


def test_semantic_bearing_filed_documents_are_not_reclassified_as_metadata_by_filtering():
    data = _load(DECISION)
    assert data["decision"] == "SEMANTICALLY_BEARING_FILED_PRODUCT_DOCUMENTS_ARE_NOT_PRESELECTION_METADATA_BY_FIELD_FILTERING"
    filed = data["authoritative_observations"]["regulator_hosted_filed_product_documents"]
    assert filed["preselection_admissible"] is False
    assert filed["boundary_classification"] == "SEMANTICALLY_BEARING_DOCUMENT"
    assert "policy_wording" in data["forbidden_preselection_source_classes"]
    assert "prospectus" in data["forbidden_preselection_source_classes"]
    assert "customer_information_sheet" in data["forbidden_preselection_source_classes"]


def test_allowed_classification_evidence_is_bounded_by_source_structure_before_projection():
    data = _load(DECISION)
    rule = data["blindness_rule"]
    assert "bounded by source structure before selector projection" in rule["principle"]
    assert rule["target_clause_reads_before_selection"] == 0
    assert rule["semantic_fit_selection"] is False
    assert rule["raw_location_exposure"] is False
    assert "regulator_product_registry_row" in data["allowed_preselection_source_classes"]
    assert "structurally_isolated_filing_cover_sheet_with_frozen_allowed_fields" in data["allowed_preselection_source_classes"]


def test_unresolved_predicates_remain_fail_closed_and_product14_stays_blocked():
    data = _load(DECISION)
    impact = data["impact_on_c5_23"]
    assert impact["benefit_basis"] == "NOT_YET_DEMONSTRATED_THROUGH_ADMISSIBLE_METADATA_SOURCE"
    assert impact["insurance_object_type"] == "PARTIALLY_METADATA_ESTABLISHABLE_BUT_NOT_UNIVERSALLY_DEMONSTRATED"
    assert impact["coverage_arrangement"] == "NOT_YET_DEMONSTRATED_THROUGH_ADMISSIBLE_METADATA_SOURCE"
    assert impact["structural_ceiling_proven"] is False
    assert impact["product14_authorized"] is False


def test_next_authorization_is_structured_classification_evidence_path_proof_only():
    auth = _load(AUTH)
    assert auth["authorized_next_action"] == "HEALTH_STRUCTURED_CLASSIFICATION_EVIDENCE_PATH_PROOF_ONLY"
    assert auth["forbidden"]["semantic_bearing_filed_product_document_parse_for_classification"] is True
    assert auth["forbidden"]["target_clause_reads"] is True
    assert auth["forbidden"]["runtime_change"] is True
    assert auth["forbidden"]["selector_projection_change"] is True
    assert auth["forbidden"]["product14_preregistration"] is True
    assert auth["forbidden"]["product14_execution"] is True
    assert auth["forbidden"]["motor"] is True
