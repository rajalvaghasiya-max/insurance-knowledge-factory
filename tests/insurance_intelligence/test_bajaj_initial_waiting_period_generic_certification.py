from __future__ import annotations

from pathlib import Path

from insurance_intelligence.rule_certification.case_loader import (
    load_rule_certification_case_file,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification


CASE_PATH = Path(
    "knowledge/factory/registry_backed/bajaj_allianz_general_my_health_care/"
    "generic_rule_certification/initial_waiting_period_certification_case.json"
)
CURRENT_SHA = "05dc291324340d5293f9f5f430f44b14e3da34052d6357455714af2dfa499158"


def test_bajaj_initial_waiting_period_loads_as_governed_data():
    case = load_rule_certification_case_file(CASE_PATH)

    assert case.case_id == "bajaj_my_health_care_initial_waiting_period"
    assert case.domain == "health"
    assert case.expected_outcome == "PASS"
    assert case.expectation.topic_id == "waiting_period"
    assert {item.component_id for item in case.expectation.component_expectations} == {
        "waiting_period_duration",
        "waiting_period_subject",
        "start_basis",
        "applicability_scope",
        "continuity_or_credit_rule",
        "exception_condition",
    }


def test_bajaj_initial_waiting_period_is_anchored_only_to_current_source():
    case = load_rule_certification_case_file(CASE_PATH)

    evidence = case.evidence_output.evidence_packages
    assert evidence
    assert {item.lineage.source_artifact_sha256 for item in evidence} == {CURRENT_SHA}
    assert {item.page for item in evidence} == {21}
    claims = " ".join(item.claim for item in evidence)
    assert "30 days" in claims
    assert "first Policy commencement date" in claims
    assert "Accident" in claims
    assert "continuous coverage for more than 12 months" in claims


def test_bajaj_initial_waiting_period_passes_generic_rule_certification():
    case = load_rule_certification_case_file(CASE_PATH)

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert result.outcome == case.expected_outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert all(check.passed for check in result.component_checks)
    assert any("unrelated Bajaj waiting-period residue remains unresolved" in item for item in result.limitations)
