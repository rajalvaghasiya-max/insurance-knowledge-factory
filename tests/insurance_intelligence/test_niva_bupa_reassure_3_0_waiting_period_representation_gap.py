from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load() -> dict:
    path = ROOT / "docs/architecture/niva_bupa_reassure_3_0_waiting_period_representation_gap_2026-08-24.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_product5_waiting_period_gap_is_recorded_before_extension() -> None:
    data = _load()

    assert data["concept"] == "waiting_period"
    assert data["repeatability_classification"]["classification"] == "REPRESENTATION_GAP"
    assert data["repeatability_classification"]["runtime_change_during_initial_attempt"] is False
    assert data["repeatability_classification"]["coercion_attempted"] is False
    assert data["repeatability_classification"]["certification_blocked"] is True


def test_personal_waiting_period_is_not_coerced_to_benefit_specific() -> None:
    data = _load()
    boundary = data["pre_existing_contract_boundary"]
    blocking = data["blocking_mechanic"]

    assert blocking["candidate_id"] == "candidate_page_33"
    assert blocking["candidate_text_sha256"] == "74408d4896f75d5127ed7ef4109bd7229a184c9c2589a6ac5dfe30f653579015"
    assert "BENEFIT_SPECIFIC" in boundary["waiting_period_types_available_before_product_selection"]
    assert "silently change the source meaning" in boundary["why_not_benefit_specific"]


def test_standard_reassure_waits_remain_existing_shapes() -> None:
    data = _load()
    mechanics = {item["mechanic"]: item for item in data["reusable_mechanics_observed"]}

    assert mechanics["PRE_EXISTING_DISEASE"]["duration"] == "36 MONTHS"
    assert mechanics["SPECIFIC_DISEASE_PROCEDURE"]["duration"] == "24 MONTHS"
    assert mechanics["INITIAL"]["duration"] == "30 DAYS"
    assert all(item["existing_shape"] is True for item in mechanics.values())


def test_v2_protocol_effect_marks_product5_repeatability_not_proven() -> None:
    data = _load()
    effect = data["protocol_effect"]

    assert effect["concept_repeatability"] == "NOT_PROVEN_FOR_CONCEPT"
    assert effect["overall_product5_strong_repeatability_possible"] is False
    assert effect["overall_product5_minimum_repeatability_possible"] is False
    assert effect["overall_product5_outcome_if_no_other_failure"] == "REPEATABILITY_NOT_PROVEN"
    assert data["governance"]["extension_counts_as_initial_repeatability_success"] is False
