from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.rule_certification.fixtures import (
    RuleCertificationCaseFixture,
    build_blocked_missing_waiting_period_case,
    build_complete_conditional_obligation_case,
    build_conflicting_waiting_period_case,
    build_partial_coverage_limit_case,
    generic_rule_certification_cases,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification


def test_complete_conditional_obligation_fixture_passes_through_real_runner():
    case = build_complete_conditional_obligation_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True


def test_partial_coverage_limit_fixture_passes_expected_partial_behaviour():
    case = build_partial_coverage_limit_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "PARTIAL"
    assert result.actual_explanation_permitted is False
    assert "limit_basis" in {
        check.component_id for check in result.component_checks if check.actual_status == "MISSING"
    }


def test_conflicting_waiting_period_fixture_certifies_expected_safe_blocking():
    case = build_conflicting_waiting_period_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "CONFLICTING"
    assert result.actual_explanation_permitted is False


def test_deliberately_unmet_waiting_period_fixture_returns_blocked():
    case = build_blocked_missing_waiting_period_case()

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == "BLOCKED"
    assert result.actual_completeness_status == "NOT_AVAILABLE"
    assert result.actual_explanation_permitted is False
    assert result.failures


def test_generic_case_catalogue_is_deterministic_unique_and_materially_diverse():
    cases = generic_rule_certification_cases()

    assert cases == tuple(sorted(cases, key=lambda item: item.case_id))
    assert len({case.case_id for case in cases}) == len(cases)
    assert {case.expectation.topic_id for case in cases} >= {
        "conditional_obligation",
        "coverage_limit",
        "waiting_period",
    }
    assert {case.expected_outcome for case in cases} >= {"PASS", "BLOCKED"}


@pytest.mark.parametrize("case", generic_rule_certification_cases())
def test_every_generic_fixture_produces_its_declared_runner_outcome(
    case: RuleCertificationCaseFixture,
):
    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == case.expected_outcome
    assert result.certification_id == case.case_id


def test_fixture_is_immutable():
    case = build_complete_conditional_obligation_case()

    with pytest.raises(FrozenInstanceError):
        case.case_id = "changed"  # type: ignore[misc]


def test_fixture_catalogue_has_no_insurer_product_plan_uin_or_document_identifiers():
    tokens = set()
    for case in generic_rule_certification_cases():
        values = (
            case.case_id,
            case.description,
            case.domain,
            case.expectation.certification_id,
            case.expectation.governed_subject_reference,
            case.expectation.topic_id,
            case.expectation.topic_version,
            case.evidence_output.request_id,
            case.evidence_output.resolution_id,
        )
        for value in values:
            tokens.update(value.lower().replace(":", "_").replace("-", "_").split("_"))

    forbidden = {"star", "aditya", "bajaj", "insurer", "product", "uin"}
    assert not tokens.intersection(forbidden)
    assert not any(token.startswith("plan") for token in tokens)
