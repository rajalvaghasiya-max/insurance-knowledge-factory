from __future__ import annotations

import json
from pathlib import Path


DECISION_PATH = Path(
    "docs/architecture/ACTIV_ONE_NXT_WAITING_PERIOD_REVIEW_DECISION.json"
)


def _load() -> dict:
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))


def _decision(payload: dict, waiting_period_type: str) -> dict:
    return next(
        item
        for item in payload["decisions"]
        if item["waiting_period_type"] == waiting_period_type
    )


def test_decision_binds_exact_activ_one_nxt_source_identity() -> None:
    payload = _load()
    assert payload["record_type"] == "waiting_period_review_decision_v1"
    assert payload["product_reference"] == "pv_aditya_birla_health_activ_one_nxt_adihlip24097v012324"
    assert payload["uin"] == "ADIHLIP24097V012324"
    assert payload["source_document_id"] == "doc_d20a8488ecb3243f6de2"
    assert payload["processed_document_asset_id"] == "pdoc_72d03e57d4b49c68d69a11fc"
    assert payload["source_document_sha256"] == "e04bc4575d35e10bc86707ceeb839adf8a59f579bd27584c1b9000201bdac217"
    assert payload["review_status"] == "APPROVED_FOR_GOVERNED_PROJECTION"
    assert payload["reviewed_by_human"] is True


def test_ped_decision_uses_base_clause_plus_product_table_duration() -> None:
    payload = _load()
    decision = _decision(payload, "PRE_EXISTING_DISEASE")
    assert decision["base_candidate_ids"] == ["wp_candidate_124e9d18ecae07d9ed02"]
    assert "wp_candidate_79345b48238f58ab1113" in decision["supporting_candidate_ids"]
    mechanics = decision["reviewed_mechanics"]
    assert mechanics["duration_value"] == 3
    assert mechanics["duration_unit"] == "YEARS"
    assert "Product Benefit Table" in mechanics["duration_evidence_note"]
    assert mechanics["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"


def test_specific_disease_decision_preserves_24_month_base() -> None:
    payload = _load()
    decision = _decision(payload, "SPECIFIC_DISEASE_PROCEDURE")
    mechanics = decision["reviewed_mechanics"]
    assert mechanics["duration_value"] == 24
    assert mechanics["duration_unit"] == "MONTHS"
    assert mechanics["start_basis"] == "INSURED_PERSON_FIRST_COVERAGE"
    assert "claims arising due to an accident" in mechanics["exceptions"]
    assert "longer waiting period applies" in mechanics["interaction_rule"]


def test_specific_disease_optional_one_year_reduction_is_rejected_for_base() -> None:
    payload = _load()
    decision = _decision(payload, "SPECIFIC_DISEASE_PROCEDURE")
    rejected = {item["candidate_id"]: item["reason"] for item in decision["rejected_candidates"]}
    assert "wp_candidate_9f5911d869ebf7ead6dc" in rejected
    assert "1 year" in rejected["wp_candidate_9f5911d869ebf7ead6dc"]
    assert "Optional Cover" in rejected["wp_candidate_9f5911d869ebf7ead6dc"]


def test_ped_optional_reduction_and_chronic_waiver_are_rejected_for_base() -> None:
    payload = _load()
    decision = _decision(payload, "PRE_EXISTING_DISEASE")
    rejected_ids = {item["candidate_id"] for item in decision["rejected_candidates"]}
    assert "wp_candidate_9f5911d869ebf7ead6dc" in rejected_ids
    assert "wp_candidate_2674ab463a53232c56df" in rejected_ids
    assert "wp_candidate_3666cf6d3d05d9c05696" in rejected_ids
    assert "wp_candidate_eea6ae76e44f1350d16b" in rejected_ids


def test_initial_decision_preserves_base_30_day_mechanic() -> None:
    payload = _load()
    decision = _decision(payload, "INITIAL")
    mechanics = decision["reviewed_mechanics"]
    assert decision["base_candidate_ids"] == ["wp_candidate_b962d57da994bcbe774f"]
    assert mechanics["duration_value"] == 30
    assert mechanics["duration_unit"] == "DAYS"
    assert mechanics["start_basis"] == "POLICY_INCEPTION"
    assert "covered claims arising due to an accident" in mechanics["exceptions"]
    assert any("more than twelve months" in item for item in mechanics["exceptions"])


def test_review_decision_does_not_publish_or_promote_registry() -> None:
    payload = _load()
    boundary = payload["publication_boundary"]
    assert boundary["runtime_publication_created"] is False
    assert boundary["coverage_registry_promoted"] is False
