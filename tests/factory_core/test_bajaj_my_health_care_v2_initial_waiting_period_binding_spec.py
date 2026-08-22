from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = (
    ROOT
    / "docs"
    / "architecture"
    / "bajaj_my_health_care_v2_initial_waiting_period_binding_spec.json"
)


def _load() -> dict:
    return json.loads(SPEC.read_text(encoding="utf-8"))


def test_spec_binds_exact_current_v2_mechanism_and_schedule_value_candidates() -> None:
    spec = _load()
    assert spec["binding_type"] == "waiting_period_binding_v1"
    assert spec["evidence_selections"] == [
        {
            "role": "mechanism",
            "document_id": "bajaj_my_health_care_policy_wording_v2",
            "candidate_id": "candidate_page_21",
            "candidate_text_sha256": "340937bc3ce71aa957c9dad8cfb306d34f343f054100a640720c885680972123",
        },
        {
            "role": "schedule_value_resolution",
            "document_id": "bajaj_my_health_care_policy_wording_v2",
            "candidate_id": "candidate_page_53",
            "candidate_text_sha256": "b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40",
        },
    ]


def test_initial_wait_preserves_clause_effects_and_schedule_selected_origin() -> None:
    spec = _load()
    mechanic = spec["mechanic"]
    assert mechanic["waiting_period_type"] == "INITIAL"
    assert mechanic["duration_value"] == 30
    assert mechanic["duration_unit"] == "DAYS"
    assert mechanic["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert "Plan 1 table resolves" in mechanic["schedule_dependency"]
    assert set(mechanic["exclusions_or_exceptions"]) == {
        "accident_claims_where_other_policy_terms_cover_the_claim",
        "insured_beneficiary_with_continuous_coverage_for_more_than_12_months",
    }
    assert (
        mechanic["sum_insured_enhancement_effect"]
        == "REAPPLIES_TO_ENHANCED_PORTION"
    )
    assert "additional_material_effects_not_collapsed_into_scalar_duration" not in spec


def test_scalar_manufacturing_is_resolved_but_publication_remains_blocked() -> None:
    spec = _load()
    assert spec["manufacturing_status"] == "resolved_scalar_ready_for_binding"
    assert spec["governance"]["scalar_binding_authorized"] is True
    assert spec["governance"]["publication_authorized"] is False
    assert spec["governance"]["policy_specific_eligibility_authorized"] is False
    assert spec["governance"]["schedule_resolution_basis"] == (
        "candidate_page_53 Plan 1 waiting-period table"
    )
