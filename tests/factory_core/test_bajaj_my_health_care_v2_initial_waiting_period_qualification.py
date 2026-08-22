from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BINDING_SPEC = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_initial_waiting_period_binding_spec.json"
QUALIFICATION = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_initial_waiting_period_qualification_2026-08-22.json"


def _binding_spec() -> dict:
    return json.loads(BINDING_SPEC.read_text(encoding="utf-8"))


def _qualification() -> dict:
    return json.loads(QUALIFICATION.read_text(encoding="utf-8"))


def test_committed_binding_spec_preserves_exact_dual_evidence_resolution() -> None:
    spec = _binding_spec()
    mechanic = spec["mechanic"]
    assert spec["manufacturing_status"] == "resolved_scalar_ready_for_binding"
    assert mechanic["waiting_period_type"] == "INITIAL"
    assert mechanic["duration_value"] == 30
    assert mechanic["duration_unit"] == "DAYS"
    assert mechanic["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert mechanic["start_basis"] == "POLICY_INCEPTION"
    assert mechanic["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"
    by_role = {item["role"]: item for item in spec["evidence_selections"]}
    assert set(by_role) == {"mechanism", "schedule_value_resolution"}
    assert by_role["mechanism"] == {
        "role": "mechanism",
        "document_id": "bajaj_my_health_care_policy_wording_v2",
        "candidate_id": "candidate_page_21",
        "candidate_text_sha256": "340937bc3ce71aa957c9dad8cfb306d34f343f054100a640720c885680972123",
    }
    assert by_role["schedule_value_resolution"] == {
        "role": "schedule_value_resolution",
        "document_id": "bajaj_my_health_care_policy_wording_v2",
        "candidate_id": "candidate_page_53",
        "candidate_text_sha256": "b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40",
    }


def test_qualification_is_ready_for_binding_reexecution_and_rule_certification() -> None:
    qualification = _qualification()
    state = qualification["qualification"]
    assert state["scalar_binding"] == "QUALIFIED"
    assert state["typed_material_effect_completeness"] == "QUALIFIED"
    assert state["rule_certification"] == "READY_AFTER_CURRENT_BINDING_REEXECUTION"
    assert state["coverage_registry_status"] == "PARTIAL"
    assert state["comparison_ready"] is False
    assert state["decision_support_ready"] is False
    assert qualification["qualified_mechanic"]["sum_insured_enhancement_effect"] == "REAPPLIES_TO_ENHANCED_PORTION"


def test_unresolved_waiting_period_families_keep_overall_concept_partial() -> None:
    qualification = _qualification()
    assert set(qualification["unresolved_waiting_period_families"]) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "MATERNITY",
        "BABY_CARE",
    }
