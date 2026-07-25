from pathlib import Path

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationExecutionStatus,
    EvaluationVerdict,
    ModelExecutionTrace,
)
from insurance_intelligence.evaluation import (
    DeterministicEvaluatorError,
    DeterministicLLMEvaluator,
    load_evaluation_dataset,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "insurance_intelligence" / "llm_evaluation"


@pytest.fixture(scope="module")
def dataset():
    return load_evaluation_dataset(FIXTURES)


def case(dataset, case_id):
    return next(item for item in dataset.cases if item.case_id == case_id)


def trace(case_id, output, *, status=EvaluationExecutionStatus.COMPLETED):
    return ModelExecutionTrace(
        trace_id=f"trace-{case_id}",
        input_id=f"input-{case_id}",
        case_id=case_id,
        provider="fixture",
        model="fixture-model",
        model_version="1",
        prompt_version="1",
        parameters=(),
        run_number=1,
        status=status,
        output_text=output if status is EvaluationExecutionStatus.COMPLETED else None,
        error_message=("provider failed" if status is EvaluationExecutionStatus.PROVIDER_ERROR else None),
    )


def test_complete_star_baseline_passes(dataset):
    item = case(dataset, "hist-004")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, item.reference_output))
    assert result.verdict is EvaluationVerdict.PASSED
    assert result.failed_check_ids == ()


def test_original_when_where_regression_fails(dataset):
    item = case(dataset, "hist-001")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, item.reference_output))
    assert result.verdict is EvaluationVerdict.FAILED
    assert "MISSING_CONDITION" in result.failure_codes


def test_missing_exception_is_reported(dataset):
    item = case(dataset, "hist-002")
    output = "A 10% co-payment applies where age at entry is 61 years or above."
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, output))
    assert "MISSING_EXCEPTION" in result.failure_codes
    assert "requirement:hist-002-1" in result.failed_check_ids


def test_missing_scope_is_reported(dataset):
    item = case(dataset, "hist-003")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "A 10% co-payment applies."))
    assert "MISSING_SCOPE" in result.failure_codes


def test_numerical_alteration_is_reported(dataset):
    item = case(dataset, "kb-004")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "A 20% co-payment applies."))
    assert "NUMERICAL_ALTERATION" in result.failure_codes


def test_certainty_inflation_is_reported(dataset):
    item = case(dataset, "kb-005")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "It definitely applies."))
    assert "CERTAINTY_INFLATION" in result.failure_codes


def test_unsupported_recommendation_is_reported(dataset):
    item = case(dataset, "kb-006")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "There is a 10% co-payment. You should buy this plan."))
    assert "UNSUPPORTED_RECOMMENDATION" in result.failure_codes


def test_claim_payment_prediction_is_reported(dataset):
    item = case(dataset, "kb-007")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "There is a 10% co-payment and the claim will be paid."))
    assert "CLAIM_PAYMENT_PREDICTION" in result.failure_codes


def test_citation_mismatch_is_reported(dataset):
    item = case(dataset, "adv-002")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "Source: ev-unapproved-source"))
    assert "CITATION_MISMATCH" in result.failure_codes


def test_governed_citation_passes(dataset):
    item = case(dataset, "adv-002")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "Source: ev-star-copay-reviewed-statement"))
    assert "CITATION_MISMATCH" not in result.failure_codes


def test_unsupported_fact_is_reported(dataset):
    item = case(dataset, "adv-001")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "The plan has a 10% co-payment and covers everything."))
    assert "UNSUPPORTED_FACT" in result.failure_codes


def test_fact_implication_confusion_is_reported(dataset):
    item = case(dataset, "adv-004")
    output = "A 10% co-payment applies to each and every claim; therefore the claim will be paid."
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, output))
    assert "FACT_IMPLICATION_CONFUSION" in result.failure_codes


def test_failure_to_abstain_is_reported(dataset):
    item = case(dataset, "adv-006")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "A 10% co-payment definitely applies."))
    assert "FAILURE_TO_ABSTAIN" in result.failure_codes


def test_explicit_abstention_avoids_failure(dataset):
    item = case(dataset, "adv-006")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "The record mentions a 10% co-payment, but applicability cannot be confirmed."))
    assert "FAILURE_TO_ABSTAIN" not in result.failure_codes


def test_review_expected_case_returns_requires_review(dataset):
    item = case(dataset, "kg-004")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "Applicability remains unresolved."))
    assert result.verdict is EvaluationVerdict.REQUIRES_REVIEW


def test_non_completed_trace_is_not_evaluated(dataset):
    item = case(dataset, "kg-001")
    result = DeterministicLLMEvaluator().evaluate(
        item,
        trace(item.case_id, None, status=EvaluationExecutionStatus.PROVIDER_ERROR),
    )
    assert result.verdict is EvaluationVerdict.NOT_EVALUATED
    assert result.limitations == ("execution_status:PROVIDER_ERROR",)


def test_case_mismatch_fails_closed(dataset):
    item = case(dataset, "kg-001")
    with pytest.raises(DeterministicEvaluatorError, match="case_id"):
        DeterministicLLMEvaluator().evaluate(item, trace("kg-002", "text"))


def test_check_and_failure_ordering_is_stable(dataset):
    item = case(dataset, "kb-001")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, item.reference_output))
    assert result.passed_check_ids == tuple(sorted(result.passed_check_ids))
    assert result.failed_check_ids == tuple(sorted(result.failed_check_ids))
    assert result.failure_codes == tuple(sorted(result.failure_codes))


def test_default_result_id_is_stable(dataset):
    item = case(dataset, "kg-005")
    result = DeterministicLLMEvaluator().evaluate(item, trace(item.case_id, "This customer explanation describes a 10% co-payment."))
    assert result.result_id == "deterministic-trace-kg-005"
