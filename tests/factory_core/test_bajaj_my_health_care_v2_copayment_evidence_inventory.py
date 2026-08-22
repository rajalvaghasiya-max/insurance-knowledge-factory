from __future__ import annotations

import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
INVENTORY = (
    REPOSITORY_ROOT
    / "docs"
    / "architecture"
    / "bajaj_my_health_care_v2_copayment_evidence_inventory_2026-08-22.json"
)
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def _load() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


def test_inventory_is_bound_to_current_v2_source() -> None:
    inventory = _load()

    assert inventory["product_identity"]["uin"] == "BAJHLIP26074V022526"
    assert inventory["source"]["document_id"] == "bajaj_my_health_care_policy_wording_v2"
    assert inventory["source"]["content_sha256"] == CURRENT_SHA
    assert inventory["source"]["temporal_status_required"] == "current_observed_reviewed"
    assert "/v2/" in inventory["source"]["registration_path"]


def test_three_distinct_copayment_mechanisms_are_preserved() -> None:
    inventory = _load()
    mechanisms = inventory["copayment_mechanisms"]

    assert len(mechanisms) == 3
    assert len({item["mechanism_id"] for item in mechanisms}) == 3
    assert {item["source_page"] for item in mechanisms} == {15, 20, 33}
    assert {item["mechanism_type"] for item in mechanisms} == {"conditional_copayment_rule"}

    by_id = {item["mechanism_id"]: item for item in mechanisms}
    assert by_id["bajaj_v2_copay_lab_radiology_unapproved_reimbursement"]["rate"] == {
        "kind": "fixed_percentage",
        "value": 20,
    }
    assert by_id["bajaj_v2_copay_international_emergency_mandatory"]["rate"] == {
        "kind": "fixed_percentage",
        "value": 10,
    }
    assert by_id["bajaj_v2_copay_voluntary_inpatient_option"]["rate"] == {
        "kind": "selected_percentage_option",
        "allowed_values": [5, 10, 15, 20],
    }


def test_mechanisms_keep_trigger_scope_and_dependency_separate() -> None:
    inventory = _load()
    by_id = {item["mechanism_id"]: item for item in inventory["copayment_mechanisms"]}

    lab = by_id["bajaj_v2_copay_lab_radiology_unapproved_reimbursement"]
    international = by_id["bajaj_v2_copay_international_emergency_mandatory"]
    voluntary = by_id["bajaj_v2_copay_voluntary_inpatient_option"]

    assert "not pre-approved" in lab["trigger"]
    assert lab["policy_schedule_dependency"] is False

    assert "International Cover" in international["scope"]
    assert international["stacking"] == "in_addition_to_any_other_applicable_copayment_or_deductible"
    assert international["policy_schedule_dependency"] is True

    assert "Voluntary Co-payment option is selected" in voluntary["trigger"]
    assert voluntary["policy_schedule_dependency"] is True
    assert "No single copayment percentage" in voluntary["exception_or_non_trigger"]


def test_inventory_prohibits_flat_product_level_copayment_fact() -> None:
    inventory = _load()
    decision = inventory["governance_decision"]

    assert decision["single_product_level_copayment_fact"] == "PROHIBITED"
    assert decision["architecture_change"] == "NONE"
    assert "Bind each mechanism separately" in decision["next_gate"]
