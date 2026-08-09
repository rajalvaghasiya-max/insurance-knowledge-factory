"""Generic governed-rule certification capability."""

from insurance_intelligence.contracts.rule_certification import (
    CERTIFICATION_OUTCOMES,
    SUPPORTED_CONTRACT_VERSION,
    ComponentCertificationCheck,
    ComponentCertificationExpectation,
    RuleCertificationContractError,
    RuleCertificationExpectation,
    RuleCertificationResult,
    build_component_certification_expectation,
    build_rule_certification_expectation,
    build_rule_certification_result,
)
from insurance_intelligence.rule_certification.fixtures import (
    RuleCertificationCaseFixture,
    build_blocked_missing_waiting_period_case,
    build_complete_conditional_obligation_case,
    build_conflicting_waiting_period_case,
    build_partial_coverage_limit_case,
    generic_rule_certification_cases,
)
from insurance_intelligence.rule_certification.runner import (
    RuleCertificationRunnerError,
    run_rule_certification,
)

__all__ = [
    "CERTIFICATION_OUTCOMES",
    "SUPPORTED_CONTRACT_VERSION",
    "ComponentCertificationCheck",
    "ComponentCertificationExpectation",
    "RuleCertificationCaseFixture",
    "RuleCertificationContractError",
    "RuleCertificationExpectation",
    "RuleCertificationResult",
    "RuleCertificationRunnerError",
    "build_blocked_missing_waiting_period_case",
    "build_complete_conditional_obligation_case",
    "build_component_certification_expectation",
    "build_conflicting_waiting_period_case",
    "build_partial_coverage_limit_case",
    "build_rule_certification_expectation",
    "build_rule_certification_result",
    "generic_rule_certification_cases",
    "run_rule_certification",
]
