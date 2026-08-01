"""Regression tests from the first controlled OpenAI provider run (MO-022F)."""
from pathlib import Path

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationExecutionStatus,
    EvaluationVerdict,
    ModelExecutionTrace,
)
from insurance_intelligence.evaluation import (
    DeterministicLLMEvaluator,
    load_evaluation_dataset,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "insurance_intelligence" / "llm_evaluation"


@pytest.fixture(scope="module")
def dataset():
    return load_evaluation_dataset(FIXTURES)


def _case(dataset, case_id):
    return next(item for item in dataset.cases if item.case_id == case_id)


def _evaluate(dataset, case_id, output):
    item = _case(dataset, case_id)
    trace = ModelExecutionTrace(
        trace_id=f"first-provider-run-{case_id}",
        input_id=f"first-provider-input-{case_id}",
        case_id=case_id,
        provider="openai",
        model="gpt-5-mini-2025-08-07",
        model_version="gpt-5-mini-2025-08-07",
        prompt_version="mo-022f-controlled-rendering-v1",
        parameters=(),
        run_number=1,
        status=EvaluationExecutionStatus.COMPLETED,
        output_text=output,
    )
    return DeterministicLLMEvaluator().evaluate(item, trace)


def test_hist_001_accepts_safe_trigger_paraphrase(dataset):
    output = (
        "If the insured person was 61 years old or older when they first entered "
        "the plan, the ‘star copay’ condition applies."
    )

    result = _evaluate(dataset, "hist-001", output)

    assert result.verdict is EvaluationVerdict.PASSED
    assert result.failed_check_ids == ()


def test_kb_001_accepts_safe_trigger_paraphrase(dataset):
    output = (
        "Trigger: If the insured person’s age when they entered the policy is "
        "61 years or above.\n\n"
        "Plain-language rephrasing: If you were 61 or older when you joined the "
        "policy, the star copay rule applies to you."
    )

    result = _evaluate(dataset, "kb-001", output)

    assert result.verdict is EvaluationVerdict.PASSED
    assert result.failed_check_ids == ()


def test_hist_004_rejects_contiguous_range_for_non_contiguous_scope(dataset):
    output = (
        "If the insured person was age 61 or older when they entered the policy, "
        "a 10% co-payment applies to every claim.\n"
        "This 10% co-payment does NOT apply if the insured entered the policy "
        "before age 61 and has renewed it continuously with no break.\n"
        "This rule covers the items listed in Sections II.1 through II.25."
    )

    result = _evaluate(dataset, "hist-004", output)

    assert result.verdict is EvaluationVerdict.FAILED
    assert result.failure_codes == ("MISSING_APPLICABILITY_SCOPE",)
    assert result.failed_check_ids == ("requirement:hist-004-5",)


def test_kg_001_rejects_contiguous_range_for_non_contiguous_scope(dataset):
    output = (
        "If the insured person’s age at entry was 61 years or above, a 10% "
        "co-payment applies to each and every claim. This co-payment does not "
        "apply if the insured person entered before age 61 and has renewed "
        "continuously without a break. The rule covers Sections II.1 through II.25."
    )

    result = _evaluate(dataset, "kg-001", output)

    assert result.verdict is EvaluationVerdict.FAILED
    assert result.failure_codes == ("MISSING_APPLICABILITY_SCOPE",)
    assert result.failed_check_ids == ("requirement:kg-001-5",)


def test_kb_004_accepts_governed_percentage_correction(dataset):
    result = _evaluate(
        dataset,
        "kb-004",
        "You are responsible for a 10% co-payment.",
    )

    assert result.verdict is EvaluationVerdict.PASSED
    assert result.failed_check_ids == ()
