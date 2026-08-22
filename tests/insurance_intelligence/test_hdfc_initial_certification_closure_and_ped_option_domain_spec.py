from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSURE = ROOT / "docs" / "architecture" / "hdfc_ergo_optima_secure_v8_initial_waiting_period_certification_closure_2026-08-22.json"
PED_SPEC = ROOT / "docs" / "architecture" / "hdfc_ergo_optima_secure_v8_ped_waiting_period_option_domain_binding_spec.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_hdfc_initial_waiting_period_is_closed_as_generic_cold_start_certification() -> None:
    closure = _load(CLOSURE)
    certification = closure["certification"]
    generalization = closure["cold_start_generalization"]
    governance = closure["governance"]

    assert certification["outcome"] == "PASS"
    assert certification["completeness"] == "COMPLETE"
    assert certification["explanation_permitted"] is True
    assert certification["failures"] == []
    assert all(value == "SATISFIED" for value in certification["components"].values())
    assert generalization == {
        "generic_registration": "PASS",
        "generic_binding": "PASS",
        "generic_certification": "PASS",
        "runtime_python_changes": 0,
        "insurer_specific_runtime_code": False,
    }
    assert governance["whole_waiting_period_concept_certified"] is False
    assert governance["publication_authorized"] is False
    assert governance["coverage_registry_promotion_authorized"] is False


def test_hdfc_ped_option_domain_reuses_existing_generic_contract() -> None:
    spec = _load(PED_SPEC)

    assert spec["binding_type"] == "waiting_period_option_domain_binding_v1"
    assert spec["reviewed_by_human"] is True
    assert spec["option_domain"]["waiting_period_type"] == "PRE_EXISTING_DISEASE"
    assert spec["option_domain"]["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert spec["option_domain"]["scope_type"] == "POLICY_WIDE"
    assert spec["option_domain"]["options"] == [
        {"duration_value": 12, "duration_unit": "MONTHS"},
        {"duration_value": 24, "duration_unit": "MONTHS"},
        {"duration_value": 36, "duration_unit": "MONTHS"},
    ]


def test_hdfc_ped_option_domain_is_bound_to_exact_reviewed_candidates() -> None:
    spec = _load(PED_SPEC)
    selections = {item["role"]: item for item in spec["evidence_selections"]}

    assert selections["mechanism"] == {
        "role": "mechanism",
        "document_id": "hdfc_ergo_optima_secure_policy_wording_v8",
        "candidate_id": "candidate_page_30",
        "candidate_text_sha256": "fceba7174d309103ee95afd6ba031c8109a45d0d97ac0373381a737bb766963e",
    }
    assert selections["option_domain"] == {
        "role": "option_domain",
        "document_id": "hdfc_ergo_optima_secure_policy_wording_v8",
        "candidate_id": "candidate_page_26",
        "candidate_text_sha256": "05864e66649d506387902d20f252bb8df552372b77a2b10e09d5e10ea1557dd2",
    }


def test_hdfc_ped_duration_domain_does_not_overclaim_full_ped_mechanic() -> None:
    spec = _load(PED_SPEC)
    deferred = spec["deferred_material_mechanics"]
    governance = spec["governance"]

    assert spec["material_mechanic_semantics"] == {
        "start_basis": "INSURED_PERSON_FIRST_COVERAGE"
    }
    assert deferred["candidate_id"] == "candidate_page_31"
    assert deferred["candidate_text_sha256"] == (
        "577c2d3bcadad71005876d367b9fe60eac8f064b83d20e872e787a7f74935327"
    )
    assert governance["full_ped_mechanic_certified_by_this_slice"] is False
    assert governance["policy_instance_duration_without_schedule_authorized"] is False
    assert governance["scalar_duration_manufacturing_without_schedule_authorized"] is False
