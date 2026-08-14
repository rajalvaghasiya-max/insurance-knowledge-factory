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


def test_policy_period_hardening_preserves_source_meaning() -> None:
    data = _load()
    modern = next(
        item
        for item in data["unit_qualification"]
        if item["normative_unit_id"] == "star_arogya_modern_treatment_group_limit"
    )
    assert modern["status"] == "REPRESENTABLE_AFTER_G5_HARDENING"
    assert "PER_POLICY_PERIOD_ADDED_AS_GENERIC_TIME_SCOPE" in modern["notes"]
    assert "NO_COERCION_TO_PER_POLICY_YEAR" in modern["notes"]
    assert "COERCE_PER_POLICY_PERIOD_TO_PER_POLICY_YEAR" in data["forbidden_shortcuts"]


def test_empty_interaction_fail_open_blocker_is_resolved() -> None:
    data = _load()
    blockers = {item["id"]: item for item in data["blocking_findings"]}
    blocker = blockers["G5-B2-EMPTY-INTERACTION-FAIL-OPEN"]
    assert blocker["classification"] == "GENERIC_COMPARISON_SAFETY_GAP"
    assert blocker["status"] == "RESOLVED"
    assert "fails closed" in blocker["resolution"].lower()


def test_g5_hardening_complete_but_real_mapping_not_yet_certified() -> None:
    decision = _load()["decision"]
    assert decision["g5_generic_hardening_complete"] is True
    assert decision["g5_real_product_mapping_certified"] is False
    assert decision["ready_for_real_eight_unit_mapping"] is True
    assert decision["zero_residue_required"] is False
    assert decision["zero_silent_residue_required"] is True
