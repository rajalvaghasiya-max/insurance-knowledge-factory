from __future__ import annotations

import json
from pathlib import Path


ARTIFACT = Path("docs/architecture/MO_028C_G5_STAR_AROGYA_REAL_PRODUCT_MAPPING_QUALIFICATION.json")


def _load() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_g5_accounts_for_all_eight_g0_units_without_forcing_mapping() -> None:
    data = _load()
    units = data["unit_qualification"]
    assert data["source_inventory_atomic_unit_count"] == 8
    assert len(units) == 8
    assert len({item["normative_unit_id"] for item in units}) == 8


def test_policy_period_is_not_coerced_to_policy_year() -> None:
    data = _load()
    modern = next(
        item
        for item in data["unit_qualification"]
        if item["normative_unit_id"] == "star_arogya_modern_treatment_group_limit"
    )
    assert modern["status"] == "BLOCKED_BY_GENERIC_TIME_SCOPE_GAP"
    assert "MUST_NOT_COERCE_TO_PER_POLICY_YEAR" in modern["notes"]
    assert "COERCE_PER_POLICY_PERIOD_TO_PER_POLICY_YEAR" in data["forbidden_shortcuts"]


def test_empty_interaction_set_is_recorded_as_generic_fail_open_blocker() -> None:
    data = _load()
    blockers = {item["id"]: item for item in data["blocking_findings"]}
    blocker = blockers["G5-B2-EMPTY-INTERACTION-FAIL-OPEN"]
    assert blocker["classification"] == "GENERIC_COMPARISON_SAFETY_GAP"
    assert "empty interaction set must block equivalence" in blocker["required_fix"].lower()


def test_g5_is_not_prematurely_certified() -> None:
    decision = _load()["decision"]
    assert decision["g5_real_product_mapping_certified"] is False
    assert decision["implementation_may_continue_after_blockers_fixed"] is True
    assert decision["zero_residue_required"] is False
    assert decision["zero_silent_residue_required"] is True
