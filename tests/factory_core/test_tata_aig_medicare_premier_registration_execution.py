import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "docs/architecture/tata_aig_medicare_premier_generic_registration_execution_2026-08-23.json"
EXPECTED_SHA256 = "392feaeeb26cb9ec7f6addc3ed764291d9c9f16bf6c70f466d9f92f85db78960"


def _checkpoint():
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def test_tata_generic_registration_execution_passed_without_runtime_change() -> None:
    checkpoint = _checkpoint()
    assert checkpoint["source_identity"]["source_document_id_sha256"] == EXPECTED_SHA256
    assert checkpoint["execution"]["registration_status"] == "generic_sources_registered_evidence_review_required"
    assert checkpoint["execution"]["source_count"] == 1
    assert checkpoint["execution"]["evidence_candidate_count"] == 60
    assert checkpoint["execution"]["result"] == "PASS"
    measurement = checkpoint["repeatability_measurement"]
    assert measurement["generic_runtime_changed_for_registration"] is False
    assert measurement["new_runtime_files"] == 0
    assert measurement["runtime_loc_delta"] == 0
    assert measurement["decision_logic_added_in_config_or_fixtures"] == 0
    assert measurement["classification"] == "REUSE"
    assert measurement["target_concept_classification_authorized"] is False
    assert checkpoint["governance"]["generic_runtime_freeze_remains_active"] is True
    assert checkpoint["next_gate"] == "REVIEW_COPAYMENT_AND_WAITING_PERIOD_CANDIDATES_WITHOUT_RUNTIME_CHANGE"
