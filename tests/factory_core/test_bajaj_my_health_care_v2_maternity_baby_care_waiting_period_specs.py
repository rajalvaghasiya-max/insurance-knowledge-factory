from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATERNITY = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_maternity_waiting_period_binding_spec.json"
BABY_CARE = ROOT / "docs" / "architecture" / "bajaj_my_health_care_v2_baby_care_waiting_period_binding_spec.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_common(spec: dict, expected_type: str, expected_scope: str) -> None:
    assert spec["binding_type"] == "waiting_period_binding_v1"
    assert spec["manufacturing_status"] == "resolved_scalar_ready_for_binding"
    mechanic = spec["mechanic"]
    assert mechanic["waiting_period_type"] == expected_type
    assert mechanic["duration_value"] == 36
    assert mechanic["duration_unit"] == "MONTHS"
    assert mechanic["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert mechanic["scope_type"] == "BENEFIT_SCOPED"
    assert mechanic["scope_reference"] == expected_scope
    assert mechanic["value_source"] == "POLICY_SCHEDULE_SELECTED"
    assert mechanic["sum_insured_enhancement_effect"] is None

    modification, = mechanic["modifications"]
    assert modification["modification_type"] == "REDUCTION"
    assert modification["condition"] == "premium_for_long_term_policy_is_paid_upfront"
    assert modification["resulting_duration_value"] == 24
    assert modification["resulting_duration_unit"] == "MONTHS"
    assert modification["evidence_reference_ids"] == [
        "bajaj_my_health_care_policy_wording_v2:candidate_page_53:b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40"
    ]

    by_role = {item["role"]: item for item in spec["evidence_selections"]}
    assert by_role["mechanism"]["candidate_id"] == "candidate_page_21"
    assert by_role["mechanism"]["candidate_text_sha256"] == "340937bc3ce71aa957c9dad8cfb306d34f343f054100a640720c885680972123"
    assert by_role["schedule_value_resolution"]["candidate_id"] == "candidate_page_53"
    assert by_role["schedule_value_resolution"]["candidate_text_sha256"] == "b362111414b124bbcc62cd3b33d0eafe7d01b5f9305fa079cdd156ee92b8cc40"

    governance = spec["governance"]
    assert governance["publication_authorized"] is False
    assert governance["policy_specific_eligibility_authorized"] is False


def test_maternity_waiting_period_is_resolved_with_conditional_reduction_and_exception() -> None:
    spec = _load(MATERNITY)
    _assert_common(spec, "MATERNITY", "maternity_package_expenses")
    assert spec["mechanic"]["exclusions_or_exceptions"] == [
        "ectopic_pregnancy_is_not_subject_to_maternity_wait_when_other_policy_terms_cover_the_claim"
    ]


def test_baby_care_waiting_period_is_resolved_with_conditional_reduction() -> None:
    spec = _load(BABY_CARE)
    _assert_common(spec, "BABY_CARE", "baby_care")
    assert spec["mechanic"]["exclusions_or_exceptions"] == []
