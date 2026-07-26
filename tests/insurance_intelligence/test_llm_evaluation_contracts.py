from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    ControlledEvaluationReport,
    DeterministicEvaluationResult,
    EvaluationCase,
    EvaluationCaseCategory,
    EvaluationDisagreement,
    EvaluationDisagreementCategory,
    EvaluationExecutionStatus,
    EvaluationExpectedOutcome,
    EvaluationInput,
    EvaluationOutput,
    EvaluationVerdict,
    ExpectedSemanticRequirement,
    ExternalMetricDisposition,
    ExternalMetricResult,
    ForbiddenBehaviour,
    LLMEvaluationContractError,
    LLMResponsibility,
    ModelExecutionTrace,
    ModelParameter,
    ResponsibilityDecision,
    ResponsibilityDecisionStatus,
    SemanticComponent,
)


def requirement(**overrides):
    values = dict(
        requirement_id="req-trigger",
        component=SemanticComponent.TRIGGER,
        expected_text="where age at entry is 61 years or above",
        evidence_ids=("evidence-1",),
    )
    values.update(overrides)
    return ExpectedSemanticRequirement(**values)


def case(**overrides):
    values = dict(
        case_id="case-1",
        title="Preserve conditional co-payment semantics",
        category=EvaluationCaseCategory.KNOWN_GOOD,
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        audience="customer",
        governed_evidence_ids=("evidence-1",),
        approved_finding_ids=("finding-1",),
        semantic_requirements=(requirement(),),
        forbidden_behaviours=(
            ForbiddenBehaviour.MISSING_CONDITION,
            ForbiddenBehaviour.MISSING_EXCEPTION,
        ),
        expected_outcome=EvaluationExpectedOutcome.PASS,
        reference_output="The co-payment applies only under the stated condition.",
        tags=("copayment", "star-comprehensive"),
    )
    values.update(overrides)
    return EvaluationCase(**values)


def evaluation_input(**overrides):
    values = dict(
        input_id="input-1",
        case_id="case-1",
        prompt_version="prompt-v1",
        governed_evidence_ids=("evidence-1",),
        approved_finding_ids=("finding-1",),
        audience="customer",
    )
    values.update(overrides)
    return EvaluationInput(**values)


def trace(**overrides):
    values = dict(
        trace_id="trace-1",
        input_id="input-1",
        case_id="case-1",
        provider="provider-a",
        model="model-a",
        model_version="2026-07-01",
        prompt_version="prompt-v1",
        parameters=(ModelParameter("temperature", "0"),),
        run_number=1,
        status=EvaluationExecutionStatus.COMPLETED,
        output_text="The governed condition is preserved.",
        latency_ms=125,
    )
    values.update(overrides)
    return ModelExecutionTrace(**values)


def deterministic(**overrides):
    values = dict(
        result_id="det-1",
        case_id="case-1",
        trace_id="trace-1",
        verdict=EvaluationVerdict.PASSED,
        passed_check_ids=("condition-preserved",),
        failed_check_ids=(),
        failure_codes=(),
    )
    values.update(overrides)
    return DeterministicEvaluationResult(**values)


def metric(**overrides):
    values = dict(
        metric_result_id="metric-1",
        case_id="case-1",
        trace_id="trace-1",
        metric_name="HHEM",
        metric_version="2.1-open",
        disposition=ExternalMetricDisposition.SUPPORTS,
        rationale=("Output is grounded in the supplied evidence.",),
        score=0.92,
        threshold=0.8,
    )
    values.update(overrides)
    return ExternalMetricResult(**values)


def decision(**overrides):
    values = dict(
        decision_id="decision-1",
        responsibility=LLMResponsibility.PLAIN_LANGUAGE_REPHRASING,
        status=ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION,
        rationale=("Known-good cases passed and known-bad cases failed.",),
        evidence_case_ids=("case-1",),
        required_controls=("Run deterministic fidelity validation.",),
    )
    values.update(overrides)
    return ResponsibilityDecision(**values)


def test_contracts_are_frozen():
    item = case()
    with pytest.raises(FrozenInstanceError):
        item.case_id = "changed"


def test_expected_requirement_normalises_text():
    item = requirement(requirement_id=" req ", expected_text=" expected ")
    assert item.requirement_id == "req"
    assert item.expected_text == "expected"


@pytest.mark.parametrize("field", ["requirement_id", "expected_text"])
def test_expected_requirement_rejects_blank_text(field):
    values = {field: " "}
    with pytest.raises(LLMEvaluationContractError):
        requirement(**values)


def test_expected_requirement_requires_evidence():
    with pytest.raises(LLMEvaluationContractError):
        requirement(evidence_ids=())


def test_evaluation_case_preserves_governance_boundaries():
    item = case()
    assert item.governed_evidence_ids == ("evidence-1",)
    assert item.approved_finding_ids == ("finding-1",)
    assert item.responsibility is LLMResponsibility.PLAIN_LANGUAGE_REPHRASING


def test_evaluation_case_rejects_duplicate_requirement_ids():
    with pytest.raises(LLMEvaluationContractError):
        case(semantic_requirements=(requirement(), requirement(expected_text="other")))


def test_evaluation_case_rejects_duplicate_forbidden_behaviour():
    with pytest.raises(LLMEvaluationContractError):
        case(
            forbidden_behaviours=(
                ForbiddenBehaviour.UNSUPPORTED_FACT,
                ForbiddenBehaviour.UNSUPPORTED_FACT,
            )
        )


def test_historical_regression_requires_defect_id():
    with pytest.raises(LLMEvaluationContractError):
        case(category=EvaluationCaseCategory.HISTORICAL_REGRESSION)


def test_historical_regression_accepts_defect_id():
    item = case(
        category=EvaluationCaseCategory.HISTORICAL_REGRESSION,
        historical_defect_id="MO-023F",
    )
    assert item.historical_defect_id == "MO-023F"


def test_evaluation_input_requires_governed_evidence_and_findings():
    with pytest.raises(LLMEvaluationContractError):
        evaluation_input(governed_evidence_ids=())
    with pytest.raises(LLMEvaluationContractError):
        evaluation_input(approved_finding_ids=())


def test_model_parameters_require_unique_names():
    with pytest.raises(LLMEvaluationContractError):
        trace(
            parameters=(
                ModelParameter("temperature", "0"),
                ModelParameter("temperature", "0.2"),
            )
        )


def test_completed_trace_requires_output_without_error():
    with pytest.raises(LLMEvaluationContractError):
        trace(output_text=None)
    with pytest.raises(LLMEvaluationContractError):
        trace(error_message="bad")


@pytest.mark.parametrize(
    "status", [EvaluationExecutionStatus.PROVIDER_ERROR, EvaluationExecutionStatus.TIMEOUT]
)
def test_failed_trace_requires_error_without_output(status):
    item = trace(status=status, output_text=None, error_message="provider unavailable")
    assert item.error_message == "provider unavailable"
    with pytest.raises(LLMEvaluationContractError):
        trace(status=status, output_text=None, error_message=None)


def test_abstained_trace_contains_neither_output_nor_error():
    item = trace(
        status=EvaluationExecutionStatus.ABSTAINED,
        output_text=None,
        error_message=None,
    )
    assert item.output_text is None
    with pytest.raises(LLMEvaluationContractError):
        trace(
            status=EvaluationExecutionStatus.ABSTAINED,
            output_text="I abstain",
            error_message=None,
        )


def test_trace_rejects_invalid_run_number_and_latency():
    with pytest.raises(LLMEvaluationContractError):
        trace(run_number=0)
    with pytest.raises(LLMEvaluationContractError):
        trace(latency_ms=-1)


def test_passed_deterministic_result_cannot_contain_failures():
    with pytest.raises(LLMEvaluationContractError):
        deterministic(failed_check_ids=("missing-scope",), failure_codes=("MISSING_SCOPE",))


def test_failed_deterministic_result_requires_failed_checks():
    with pytest.raises(LLMEvaluationContractError):
        deterministic(verdict=EvaluationVerdict.FAILED)


def test_deterministic_check_cannot_both_pass_and_fail():
    with pytest.raises(LLMEvaluationContractError):
        deterministic(
            verdict=EvaluationVerdict.FAILED,
            passed_check_ids=("scope",),
            failed_check_ids=("scope",),
            failure_codes=("MISSING_SCOPE",),
        )


def test_not_evaluated_result_contains_no_checks():
    item = deterministic(
        verdict=EvaluationVerdict.NOT_EVALUATED,
        passed_check_ids=(),
        failed_check_ids=(),
        failure_codes=(),
    )
    assert item.verdict is EvaluationVerdict.NOT_EVALUATED
    with pytest.raises(LLMEvaluationContractError):
        deterministic(verdict=EvaluationVerdict.NOT_EVALUATED)


def test_external_metric_score_and_threshold_are_bounded():
    with pytest.raises(LLMEvaluationContractError):
        metric(score=1.1)
    with pytest.raises(LLMEvaluationContractError):
        metric(threshold=-0.1)


def test_external_support_or_flag_requires_score():
    with pytest.raises(LLMEvaluationContractError):
        metric(score=None)


def test_external_metric_error_requires_error_message():
    item = metric(
        disposition=ExternalMetricDisposition.ERROR,
        score=None,
        threshold=None,
        error_message="metric unavailable",
    )
    assert item.error_message == "metric unavailable"
    with pytest.raises(LLMEvaluationContractError):
        metric(
            disposition=ExternalMetricDisposition.ERROR,
            score=None,
            threshold=None,
            error_message=None,
        )


def test_non_error_metric_cannot_have_error_message():
    with pytest.raises(LLMEvaluationContractError):
        metric(error_message="unexpected")


def test_evaluation_output_links_trace_and_results():
    item = EvaluationOutput(
        output_id="output-1",
        input_id="input-1",
        trace=trace(),
        deterministic_result=deterministic(),
        external_metric_results=(metric(),),
    )
    assert item.trace.trace_id == "trace-1"


def test_evaluation_output_rejects_mismatched_input():
    with pytest.raises(LLMEvaluationContractError):
        EvaluationOutput(
            output_id="output-1",
            input_id="other-input",
            trace=trace(),
            deterministic_result=deterministic(),
        )


def test_evaluation_output_rejects_mismatched_result_trace():
    with pytest.raises(LLMEvaluationContractError):
        EvaluationOutput(
            output_id="output-1",
            input_id="input-1",
            trace=trace(),
            deterministic_result=deterministic(trace_id="other-trace"),
        )


def test_evaluation_output_rejects_mismatched_external_metric():
    with pytest.raises(LLMEvaluationContractError):
        EvaluationOutput(
            output_id="output-1",
            input_id="input-1",
            trace=trace(),
            deterministic_result=deterministic(),
            external_metric_results=(metric(case_id="other-case"),),
        )


def test_disagreement_categories_require_review():
    with pytest.raises(LLMEvaluationContractError):
        EvaluationDisagreement(
            disagreement_id="disagreement-1",
            case_id="case-1",
            trace_id="trace-1",
            deterministic_result_id="det-1",
            external_metric_result_id="metric-1",
            category=EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
            rationale=("External metric missed a deterministic failure.",),
            review_required=False,
        )


def test_agreement_record_may_not_require_review():
    item = EvaluationDisagreement(
        disagreement_id="agreement-1",
        case_id="case-1",
        trace_id="trace-1",
        deterministic_result_id="det-1",
        external_metric_result_id="metric-1",
        category=EvaluationDisagreementCategory.BOTH_PASS,
        rationale=("Both mechanisms accepted the output.",),
        review_required=False,
    )
    assert not item.review_required


def test_approval_with_validation_requires_controls():
    with pytest.raises(LLMEvaluationContractError):
        decision(required_controls=())


def test_rejected_responsibility_may_have_no_controls():
    item = decision(
        status=ResponsibilityDecisionStatus.REJECTED,
        required_controls=(),
    )
    assert item.status is ResponsibilityDecisionStatus.REJECTED


def test_report_requires_unique_responsibility_decisions():
    with pytest.raises(LLMEvaluationContractError):
        ControlledEvaluationReport(
            report_id="report-1",
            dataset_version="v1",
            case_ids=("case-1",),
            output_ids=("output-1",),
            disagreement_ids=(),
            responsibility_decisions=(decision(), decision(decision_id="decision-2")),
            conclusion="Do not approve without deterministic controls.",
        )


def test_report_decisions_may_reference_only_report_cases():
    with pytest.raises(LLMEvaluationContractError):
        ControlledEvaluationReport(
            report_id="report-1",
            dataset_version="v1",
            case_ids=("case-1",),
            output_ids=("output-1",),
            disagreement_ids=(),
            responsibility_decisions=(decision(evidence_case_ids=("unknown-case",)),),
            conclusion="Insufficient evidence.",
        )


def test_valid_report_preserves_final_decision_boundary():
    item = ControlledEvaluationReport(
        report_id="report-1",
        dataset_version="v1",
        case_ids=("case-1",),
        output_ids=("output-1",),
        disagreement_ids=("disagreement-1",),
        responsibility_decisions=(decision(),),
        conclusion="Plain-language rephrasing is controlled by deterministic validation.",
    )
    assert item.responsibility_decisions[0].status is (
        ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION
    )
