from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    ROOT
    / "docs"
    / "architecture"
    / "hdfc_ergo_optima_secure_v8_ped_waiting_period_full_mechanics_binding_spec.json"
)


def _spec() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_hdfc_ped_full_mechanics_uses_generic_multispan_binding() -> None:
    spec = _spec()

    assert spec["binding_type"] == "waiting_period_option_domain_multispan_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert [item["role"] for item in spec["evidence_selections"]] == [
        "mechanism",
        "mechanism",
        "option_domain",
    ]
    assert [item["candidate_id"] for item in spec["evidence_selections"]] == [
        "candidate_page_30",
        "candidate_page_31",
        "candidate_page_26",
    ]


def test_hdfc_ped_full_mechanics_preserves_schedule_selected_domain() -> None:
    domain = _spec()["option_domain"]

    assert domain["waiting_period_type"] == "PRE_EXISTING_DISEASE"
    assert domain["options"] == [
        {"duration_value": 12, "duration_unit": "MONTHS"},
        {"duration_value": 24, "duration_unit": "MONTHS"},
        {"duration_value": 36, "duration_unit": "MONTHS"},
    ]
    assert domain["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert domain["scope_type"] == "POLICY_WIDE"


def test_hdfc_ped_full_mechanics_preserves_page_31_semantics() -> None:
    semantics = _spec()["material_mechanic_semantics"]

    assert semantics["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert "prior coverage" in semantics["continuity_credit"]
    assert semantics["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    assert "declared at application" in semantics["post_wait_condition"]
    assert "accepted by the insurer" in semantics["post_wait_condition"]


def test_hdfc_ped_full_mechanics_remains_fail_closed_for_policy_instance_use() -> None:
    governance = _spec()["governance"]

    assert governance["publication_authorized"] is False
    assert governance["policy_specific_eligibility_authorized"] is False
    assert governance["policy_instance_duration_without_schedule_authorized"] is False
    assert governance["scalar_duration_manufacturing_without_schedule_authorized"] is False
    assert governance["full_ped_mechanic_certification_authorized"] is True
