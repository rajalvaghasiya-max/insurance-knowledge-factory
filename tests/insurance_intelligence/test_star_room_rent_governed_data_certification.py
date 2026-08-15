from __future__ import annotations

import json
from pathlib import Path

import pytest

from insurance_intelligence.rule_certification.case_loader import (
    RuleCertificationCaseLoadError,
    load_rule_certification_case,
    load_rule_certification_case_file,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification
from insurance_intelligence.rule_certification.star_health_room_rent import (
    build_star_comprehensive_room_rent_case,
)


CASE_PATH = Path(
    "knowledge/factory/registry_backed/star_health_star_comprehensive/"
    "generic_rule_certification/room_rent_certification_case.json"
)


def test_governed_data_case_is_semantically_identical_to_legacy_python_case():
    legacy = build_star_comprehensive_room_rent_case()
    loaded = load_rule_certification_case_file(CASE_PATH)

    assert loaded.case_id == legacy.case_id
    assert loaded.description == legacy.description
    assert loaded.domain == legacy.domain
    assert loaded.expected_outcome == legacy.expected_outcome
    assert loaded.expectation == legacy.expectation
    assert loaded.evidence_output == legacy.evidence_output


def test_governed_data_case_passes_unchanged_generic_runner():
    case = load_rule_certification_case_file(CASE_PATH)

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == case.expected_outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert tuple(check.component_id for check in result.component_checks) == (
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
        "excess_consequence",
    )
    assert all(check.passed for check in result.component_checks)


def test_governed_data_preserves_room_category_and_proportional_consequence():
    case = load_rule_certification_case_file(CASE_PATH)
    claims = {item.field_or_topic: item.claim for item in case.evidence_output.evidence_packages}

    assert "Private Single A/C room" in claims["LIMIT_VALUE"]
    assert "no separate monetary room-rent cap" in claims["LIMIT_VALUE"]
    assert "proportionately" in claims["EXCESS_CONSEQUENCE"]
    assert "vary based on the room rent" in claims["APPLICABILITY_SCOPE"]
    assert any(
        "does not guarantee admissibility or payment" in limitation
        for limitation in case.evidence_output.limitations
    )


def test_loader_fails_closed_on_unknown_top_level_key():
    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    payload["product_specific_logic"] = "forbidden"

    with pytest.raises(RuleCertificationCaseLoadError, match="extra=.*product_specific_logic"):
        load_rule_certification_case(payload)


def test_loader_fails_closed_on_invalid_expected_outcome():
    payload = json.loads(CASE_PATH.read_text(encoding="utf-8"))
    payload["expected_outcome"] = "AUTO_PUBLISH"

    with pytest.raises(RuleCertificationCaseLoadError, match="expected_outcome"):
        load_rule_certification_case(payload)
