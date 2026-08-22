from __future__ import annotations

import json
from pathlib import Path

from factory_core.canonical.waiting_period_binding import WaitingPeriodBinding


ROOT = Path(__file__).resolve().parents[2]
BINDING_SPEC = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_initial_waiting_period_binding_spec.json"
QUALIFICATION = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_initial_waiting_period_qualification_2026-08-22.json"


def _qualification() -> dict:
    return json.loads(QUALIFICATION.read_text(encoding="utf-8"))


def test_real_v2_initial_wait_binding_resolves_from_two_authoritative_candidates() -> None:
    result = WaitingPeriodBinding().bind_from_spec_file(
        spec_path=BINDING_SPEC,
        repository_root=ROOT,
        bound_at="2026-08-22T00:00:00+00:00",
    )
    manifest = result.manifest
    assert manifest["binding_status"] == "reviewed_waiting_period_bound_not_published"
    assert manifest["resolution_status"] == "resolved_from_authoritative_schedule_evidence"
    assert manifest["publication_status"] == "bound_not_published"
    mechanic = manifest["mechanic"]
    assert mechanic["waiting_period_type"] == "INITIAL"
    assert mechanic["duration_value"] == 30
    assert mechanic["duration_unit"] == "DAYS"
    assert mechanic["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert mechanic["start_basis"] == "POLICY_INCEPTION"
    assert {item["role"] for item in manifest["evidence"]} == {
        "mechanism",
        "schedule_value_resolution",
    }
    by_role = {item["role"]: item for item in manifest["evidence"]}
    assert by_role["mechanism"]["candidate_id"] == "candidate_page_21"
    assert by_role["schedule_value_resolution"]["candidate_id"] == "candidate_page_53"


def test_qualification_keeps_waiting_period_concept_partial() -> None:
    qualification = _qualification()
    state = qualification["qualification"]
    assert state["scalar_binding"] == "QUALIFIED"
    assert state["rule_certification"] == "DEFERRED_PENDING_TYPED_MATERIAL_EFFECT_COMPLETENESS"
    assert state["coverage_registry_status"] == "PARTIAL"
    assert state["comparison_ready"] is False
    assert state["decision_support_ready"] is False


def test_enhanced_sum_insured_reapplication_is_not_silently_lost() -> None:
    qualification = _qualification()
    remaining = qualification["remaining_material_effect"]
    assert "enhanced Sum Insured" in remaining["effect"]
    assert remaining["evidence_candidate_id"] == "candidate_page_21"
    assert remaining["typed_runtime_representation"] == "MISSING"


def test_unresolved_waiting_period_families_remain_explicitly_blocked_from_certification() -> None:
    qualification = _qualification()
    assert set(qualification["unresolved_waiting_period_families"]) == {
        "PRE_EXISTING_DISEASE",
        "SPECIFIC_DISEASE_PROCEDURE",
        "MATERNITY",
        "BABY_CARE",
    }
