from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.evaluation import (
    EvaluationContractError,
    build_assertion,
    build_assertion_result,
    build_result,
    build_scenario,
    build_stage_expectation,
)


def _scenario():
    return build_scenario(
        scenario_id="s1",
        scenario_version="1.0",
        name="Scenario",
        description="Description",
        scenario_kind="GENERAL_EXPLANATION",
        request_text="Explain the clause",
        domain="health",
        topic="conditional_copayment",
        audience="CUSTOMER",
        expected_response_statuses=("ANSWER",),
        stage_expectations=(build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",)),),
        assertions=(
            build_assertion(
                assertion_id="a1",
                category="RESPONSE_STATUS",
                description="status",
                target_stage="RESPONSE_ASSEMBLER",
                expected_values=("ANSWER",),
            ),
        ),
        required_behaviors=("preserve_condition",),
        prohibited_behaviors=("recommend_product",),
    )


def test_scenario_is_immutable_and_preserves_context():
    scenario = _scenario()
    assert scenario.registry_key == ("s1", "1.0")
    assert scenario.expected_response_statuses == ("ANSWER",)
    with pytest.raises(FrozenInstanceError):
        scenario.name = "changed"  # type: ignore[misc]


def test_stage_expectation_requires_status():
    with pytest.raises(EvaluationContractError):
        build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=())


def test_stage_expectation_rejects_required_prohibited_overlap():
    with pytest.raises(EvaluationContractError):
        build_stage_expectation(
            stage="RESPONSE_ASSEMBLER",
            expected_statuses=("ANSWER",),
            required_trace_events=("X",),
            prohibited_trace_events=("X",),
        )


def test_assertion_requires_values_for_status_category():
    with pytest.raises(EvaluationContractError):
        build_assertion(assertion_id="a", category="RESPONSE_STATUS", description="status")


def test_scenario_rejects_duplicate_stage_expectations():
    stage = build_stage_expectation(stage="RESPONSE_ASSEMBLER", expected_statuses=("ANSWER",))
    with pytest.raises(EvaluationContractError):
        build_scenario(
            scenario_id="s",
            scenario_version="1",
            name="n",
            description="d",
            scenario_kind="GENERAL_EXPLANATION",
            request_text="r",
            domain="health",
            topic="copay",
            audience="CUSTOMER",
            expected_response_statuses=("ANSWER",),
            stage_expectations=(stage, stage),
            assertions=(),
        )


def test_scenario_rejects_duplicate_assertion_ids():
    assertion = build_assertion(
        assertion_id="a", category="REQUIRED_BEHAVIOR", description="required", expected_values=("x",)
    )
    with pytest.raises(EvaluationContractError):
        build_scenario(
            scenario_id="s",
            scenario_version="1",
            name="n",
            description="d",
            scenario_kind="GENERAL_EXPLANATION",
            request_text="r",
            domain="health",
            topic="copay",
            audience="CUSTOMER",
            expected_response_statuses=("ANSWER",),
            stage_expectations=(),
            assertions=(assertion, assertion),
        )


def test_scenario_rejects_behavior_overlap():
    with pytest.raises(EvaluationContractError):
        build_scenario(
            scenario_id="s",
            scenario_version="1",
            name="n",
            description="d",
            scenario_kind="GENERAL_EXPLANATION",
            request_text="r",
            domain="health",
            topic="copay",
            audience="CUSTOMER",
            expected_response_statuses=("ANSWER",),
            stage_expectations=(),
            assertions=(),
            required_behaviors=("x",),
            prohibited_behaviors=("x",),
        )


def test_result_pass_cannot_contain_failed_assertion():
    failed = build_assertion_result(
        assertion_id="a", category="REQUIRED_BEHAVIOR", passed=False, message="missing"
    )
    with pytest.raises(EvaluationContractError):
        build_result(scenario_id="s", run_id="r", outcome="PASS", assertion_results=(failed,))


def test_result_fail_requires_failed_assertion():
    passed = build_assertion_result(
        assertion_id="a", category="REQUIRED_BEHAVIOR", passed=True, message="present"
    )
    with pytest.raises(EvaluationContractError):
        build_result(scenario_id="s", run_id="r", outcome="FAIL", assertion_results=(passed,))


def test_blocked_result_requires_reason():
    with pytest.raises(EvaluationContractError):
        build_result(scenario_id="s", run_id="r", outcome="BLOCKED", assertion_results=())


def test_valid_fail_result_derives_failed_ids():
    failed = build_assertion_result(
        assertion_id="a", category="PROHIBITED_BEHAVIOR", passed=False, actual_values=("recommend",), message="found"
    )
    result = build_result(scenario_id="s", run_id="r", outcome="FAIL", assertion_results=(failed,))
    assert result.failed_assertion_ids == ("a",)
