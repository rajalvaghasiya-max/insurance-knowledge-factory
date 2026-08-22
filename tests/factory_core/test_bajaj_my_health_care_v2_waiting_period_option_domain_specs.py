from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PED = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_ped_waiting_period_option_domain_binding_spec.json"
SPECIFIC = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_specific_disease_waiting_period_option_domain_binding_spec.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_common(spec: dict, waiting_period_type: str) -> None:
    assert spec["binding_type"] == "waiting_period_option_domain_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["option_domain"]["waiting_period_type"] == waiting_period_type
    assert spec["option_domain"]["options"] == [
        {"duration_value": 1, "duration_unit": "YEARS"},
        {"duration_value": 2, "duration_unit": "YEARS"},
        {"duration_value": 3, "duration_unit": "YEARS"},
    ]
    assert spec["option_domain"]["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert spec["evidence_selections"] == [
        {
            "role": "mechanism",
            "document_id": "bajaj_my_health_care_policy_wording_v2",
            "candidate_id": "candidate_page_20",
            "candidate_text_sha256": "5261b13c20af365078c7ec1a4b43e742fd1890257a57fa5858d6314eff87aef2",
        },
        {
            "role": "option_domain",
            "document_id": "bajaj_my_health_care_policy_wording_v2",
            "candidate_id": "candidate_page_53",
            "candidate_text_sha256": "b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40",
        },
    ]
    assert spec["governance"] == {
        "publication_authorized": False,
        "policy_instance_resolution_authorized_without_schedule": False,
        "scalar_manufacturing_authorized_without_schedule": False,
    }


def test_ped_option_domain_is_unresolved_and_preserves_material_semantics() -> None:
    spec = _load(PED)
    _assert_common(spec, "PRE_EXISTING_DISEASE")
    semantics = spec["material_mechanic_semantics"]
    assert semantics["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert semantics["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert "prior_coverage" in semantics["continuity_credit"]
    assert "accepted_by_insurer" in semantics["post_wait_condition"]


def test_specific_disease_option_domain_is_unresolved_and_preserves_material_semantics() -> None:
    spec = _load(SPECIFIC)
    _assert_common(spec, "SPECIFIC_DISEASE_PROCEDURE")
    semantics = spec["material_mechanic_semantics"]
    assert semantics["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert semantics["accident_exception"] is True
    assert semantics["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert "longer" in semantics["longer_of_relationship"]
    assert "prior_coverage" in semantics["continuity_credit"]
