from pathlib import Path

from insurance_intelligence.rule_certification.case_loader import (
    load_rule_certification_case_file,
)
from insurance_intelligence.rule_certification.runner import run_rule_certification


REPO_ROOT = Path(__file__).resolve().parents[2]
CASE_PATH = (
    REPO_ROOT
    / "knowledge"
    / "factory"
    / "registry_backed"
    / "bajaj_allianz_general_my_health_care"
    / "generic_rule_certification"
    / "cataract_si_up_to_10_lakh_coverage_limit_certification_case.json"
)


def test_bajaj_cataract_coverage_limit_case_passes_generic_certification() -> None:
    case = load_rule_certification_case_file(CASE_PATH)

    result = run_rule_certification(
        expectation=case.expectation,
        evidence_output=case.evidence_output,
        domain=case.domain,
    )

    assert case.expected_outcome == "PASS"
    assert result.outcome == "PASS"
    assert result.actual_completeness_status == "COMPLETE"
    assert result.actual_explanation_permitted is True
    assert result.failures == ()

    checks = {check.component_id: check for check in result.component_checks}
    assert set(checks) == {
        "covered_subject",
        "limit_value",
        "limit_basis",
        "applicability_scope",
    }
    assert all(check.passed for check in checks.values())


def test_bajaj_cataract_coverage_limit_preserves_bounded_residue() -> None:
    case = load_rule_certification_case_file(CASE_PATH)

    assert any("waiting-period duration" in item for item in case.evidence_output.limitations)
    assert any("Actual" in item for item in case.evidence_output.limitations)

    evidence = {item.field_or_topic: item for item in case.evidence_output.evidence_packages}
    assert evidence["LIMIT_VALUE"].claim == (
        "For Sum Insured up to INR 10 lakh, the cataract payment limit is 20% "
        "of Sum Insured with a maximum of INR 1 lakh."
    )
    assert evidence["LIMIT_BASIS"].claim == "The capped cataract limit is stated per eye."
    assert "above INR 10 lakh" not in evidence["LIMIT_VALUE"].claim
