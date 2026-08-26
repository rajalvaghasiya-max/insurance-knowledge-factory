import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DECISION = ROOT / "docs/architecture/health_benefit_basis_blind_safe_evidence_path_decision_c5_27_2026-08-26.json"
AUTH = ROOT / "docs/architecture/health_neutral_selection_measurement_apparatus_decision_authorization_v1.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_c5_27_does_not_claim_structural_ceiling():
    record = _load(DECISION)
    assert record["architecture_verdict"] == "BLIND_SELECTION_EVIDENCE_PATH_INCOMPLETE"
    assert record["structural_ceiling_proven"] is False
    assert record["establishability_under_blindness"] == "METADATA_ESTABLISHABLE_IN_PRINCIPLE_PUBLIC_PATH_NOT_DEMONSTRATED"


def test_c5_27_keeps_benefit_basis_regulatory_not_semantic_only():
    record = _load(DECISION)
    predicate = record["predicate"]
    assert predicate["predicate_id"] == "benefit_basis"
    assert predicate["layer"] == "REGULATORY_TAXONOMY"
    assert predicate["closure_type"] == "REGULATORY_DERIVED"
    assert set(predicate["allowed_values"]) == {"INDEMNITY", "BENEFIT", "UNKNOWN"}


def test_c5_27_preserves_semantic_source_firewall():
    record = _load(DECISION)
    forbidden = set(record["source_boundary"]["forbidden"])
    assert "policy wording" in forbidden
    assert "prospectus" in forbidden
    assert "customer information sheet" in forbidden
    assert "semantic-bearing filed product document filtered after parsing" in forbidden
    assert "target-clause inspection" in forbidden


def test_c5_27_does_not_authorize_product14_or_runtime_changes():
    record = _load(DECISION)
    assert record["product14_authorized"] is False
    assert record["runtime_change_authorized"] is False
    assert record["projection_change_authorized"] is False
    assert record["target_clause_reads_authorized"] is False
    assert record["motor_authorized"] is False


def test_c5_27_authorizes_measurement_apparatus_decision_only():
    auth = _load(AUTH)
    assert auth["authorized_next_action"] == "HEALTH_NEUTRAL_SELECTION_MEASUREMENT_APPARATUS_ARCHITECTURE_DECISION_ONLY"
    forbidden = auth["forbidden"]
    assert forbidden["runtime_change"] is True
    assert forbidden["selector_projection_change"] is True
    assert forbidden["product14_preregistration"] is True
    assert forbidden["product14_execution"] is True
    assert forbidden["target_clause_reads"] is True
    assert forbidden["semantic_fit_selection"] is True
    assert forbidden["motor"] is True
