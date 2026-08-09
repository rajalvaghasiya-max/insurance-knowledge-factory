from __future__ import annotations

import json
from pathlib import Path


DECISION_PATH = Path(
    "docs/architecture/STAR_COMPREHENSIVE_WAITING_PERIOD_REVIEW_DECISION.json"
)


def _decision() -> dict:
    return json.loads(DECISION_PATH.read_text(encoding="utf-8"))


def test_review_decision_uses_exact_star_product_and_source_identity() -> None:
    payload = _decision()
    assert payload["product_reference"] == "pv_star_health_star_comprehensive_shahlip26044v092526"
    assert payload["uin"] == "SHAHLIP26044V092526"
    assert payload["source_document_id"] == "star_health_star_comprehensive_policy_wording_v1"
    assert payload["source_document_sha256"] == "b1dbe8fb78646f75566d47c32b7ebfa27c4071941c8f548224c461ee35a8021f"
    assert payload["review_status"] == "APPROVED_FOR_GOVERNED_PROJECTION"
    assert payload["reviewed_by_human"] is True


def test_review_decision_selects_base_ped_and_rejects_optional_buyback() -> None:
    payload = _decision()
    ped = next(item for item in payload["decisions"] if item["waiting_period_type"] == "PRE_EXISTING_DISEASE")
    assert ped["base_candidate_ids"] == ["candidate_page_31"]
    assert ped["reviewed_mechanics"]["duration_value"] == 36
    assert ped["reviewed_mechanics"]["duration_unit"] == "MONTHS"
    assert ped["rejected_candidates"] == [
        {
            "candidate_id": "candidate_page_30",
            "reason": "Optional Cover Buy Back wording changes the PED duration from the base 36 months to 12 months and is not the base exclusion.",
        }
    ]


def test_review_decision_selects_complete_specific_disease_clause_across_pages() -> None:
    payload = _decision()
    specific = next(item for item in payload["decisions"] if item["waiting_period_type"] == "SPECIFIC_DISEASE_PROCEDURE")
    assert specific["base_candidate_ids"] == ["candidate_page_31", "candidate_page_32"]
    assert specific["reviewed_mechanics"]["duration_value"] == 24
    assert specific["reviewed_mechanics"]["duration_unit"] == "MONTHS"
    assert specific["reviewed_mechanics"]["exceptions"] == ["claims arising due to an accident"]
    assert "longer waiting period applies" in specific["reviewed_mechanics"]["interaction_rule"]


def test_review_decision_selects_initial_waiting_period_and_preserves_exceptions() -> None:
    payload = _decision()
    initial = next(item for item in payload["decisions"] if item["waiting_period_type"] == "INITIAL")
    assert initial["base_candidate_ids"] == ["candidate_page_32"]
    assert initial["reviewed_mechanics"]["duration_value"] == 30
    assert initial["reviewed_mechanics"]["duration_unit"] == "DAYS"
    assert initial["reviewed_mechanics"]["start_basis"] == "POLICY_INCEPTION"
    assert initial["reviewed_mechanics"]["exceptions"] == [
        "covered claims arising due to an accident",
        "the exclusion does not apply where the insured person has Continuous Coverage for more than twelve months",
    ]


def test_review_decision_does_not_publish_or_promote_registry() -> None:
    payload = _decision()
    assert payload["publication_boundary"] == {
        "runtime_publication_created": False,
        "coverage_registry_promoted": False,
        "reason": "This decision approves exact evidence selection and semantic projection only. Runtime publication and registry promotion require a separate tested step.",
    }
