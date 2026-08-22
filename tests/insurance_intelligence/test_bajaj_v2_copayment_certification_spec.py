from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_copayment_certification_spec.json"

EXPECTED_ASSERTIONS = {
    "ga_bajaj_my_health_care_lab_radiology_unapproved_reimbursement_copay_v1",
    "ga_bajaj_my_health_care_international_emergency_mandatory_copay_v1",
    "ga_bajaj_my_health_care_voluntary_inpatient_copay_v1",
}


def _load() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_certification_request_is_bound_to_current_bajaj_v2() -> None:
    spec = _load()

    assert spec["schema_version"] == "1.0"
    assert spec["certification_type"] == "conditional_copayment_certification_request_v1"
    assert spec["domain"] == "health"
    assert spec["product_identity"] == {
        "insurer_id": "bajaj_allianz_general",
        "product_id": "my_health_care",
        "uin": "BAJHLIP26074V022526",
    }
    assert spec["source_identity"] == {
        "document_id": "bajaj_my_health_care_policy_wording_v2",
        "content_sha256": "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158",
        "required_temporal_status": "current_observed_reviewed",
    }
    assert "/v2/" in spec["binding_manifest_path"]


def test_certification_request_selects_exact_three_governed_assertions() -> None:
    spec = _load()

    assert len(spec["assertion_ids"]) == 3
    assert set(spec["assertion_ids"]) == EXPECTED_ASSERTIONS
    assert spec["expected_certification"] == {
        "case_count": 3,
        "outcome_per_case": "PASS",
        "completeness_status_per_case": "COMPLETE",
        "explanation_permitted_per_case": True,
    }


def test_certification_request_does_not_authorize_publication_or_rate_inference() -> None:
    governance = _load()["governance"]

    assert governance["single_product_level_copayment_fact"] == "PROHIBITED"
    assert governance["publication_authorized"] is False
    assert governance["policy_specific_rate_selection_authorized"] is False
    assert governance["architecture_change"] == "NONE"
