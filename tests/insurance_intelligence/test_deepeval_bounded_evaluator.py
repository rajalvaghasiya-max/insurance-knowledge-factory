from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationExecutionStatus,
    ExternalMetricDisposition,
    ModelExecutionTrace,
)
from insurance_intelligence.evaluation.deepeval import (
    DeepEvalAdvisoryError,
    DeepEvalDependencyUnavailable,
    DeepEvalMetricConfig,
    DeepEvalMetricError,
    DeepEvalMetricRequest,
    DeepEvalMetricTimeout,
    evaluate_deepeval_metric,
    evaluate_deepeval_metrics,
)


class FakeRunner:
    def __init__(self, score: float = 0.9, error: Exception | None = None):
        self.result = score
        self.error = error
        self.requests: list[DeepEvalMetricRequest] = []

    def measure(self, request: DeepEvalMetricRequest) -> float:
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.result


def trace() -> ModelExecutionTrace:
    return ModelExecutionTrace(
        trace_id="trace-a",
        input_id="input-a",
        case_id="case-a",
        provider="fake",
        model="fake-model",
        model_version="1",
        prompt_version="p1",
        parameters=(),
        run_number=1,
        status=EvaluationExecutionStatus.COMPLETED,
        output_text="A 10% copayment applies when the stated condition is met.",
        latency_ms=1,
    )


def config(**changes: object) -> DeepEvalMetricConfig:
    values = dict(
        metric_name="FAITHFULNESS_ADVISORY",
        metric_version="1.0",
        threshold=0.8,
        timeout_seconds=2.0,
        judge_model="fake-judge",
    )
    values.update(changes)
    return DeepEvalMetricConfig(**values)


def evaluate(runner: FakeRunner, cfg: DeepEvalMetricConfig | None = None):
    return evaluate_deepeval_metric(
        trace=trace(),
        input_text="Explain the copayment.",
        expected_output="A conditional 10% copayment applies.",
        context=("Policy wording states a conditional 10% copayment.",),
        runner=runner,
        config=cfg or config(),
    )


def test_supporting_score_is_advisory_and_records_metadata() -> None:
    runner = FakeRunner(0.91)
    result = evaluate(runner)
    assert result.disposition is ExternalMetricDisposition.SUPPORTS
    assert result.score == 0.91
    assert result.threshold == 0.8
    assert result.metric_version == "1.0@fake-judge"
    assert "does not override deterministic findings" in result.rationale[1]
    assert runner.requests[0].actual_output == trace().output_text


def test_below_threshold_flags_without_authoritative_failure() -> None:
    result = evaluate(FakeRunner(0.2))
    assert result.disposition is ExternalMetricDisposition.FLAGS
    assert "advisory" in result.rationale[1].lower()


@pytest.mark.parametrize(
    "error",
    [
        DeepEvalDependencyUnavailable("dependency unavailable"),
        DeepEvalMetricTimeout("timed out"),
        DeepEvalMetricError("metric failed"),
    ],
)
def test_controlled_failures_return_error_results(error: Exception) -> None:
    result = evaluate(FakeRunner(error=error))
    assert result.disposition is ExternalMetricDisposition.ERROR
    assert result.error_message == str(error)


def test_unexpected_runner_exception_fails_closed() -> None:
    result = evaluate(FakeRunner(error=RuntimeError("boom")))
    assert result.disposition is ExternalMetricDisposition.ERROR
    assert result.error_message == "RuntimeError: boom"


@pytest.mark.parametrize("score", [-0.1, 1.1, True, "bad"])
def test_invalid_runner_output_is_recorded_as_error(score: object) -> None:
    runner = FakeRunner()
    runner.result = score  # type: ignore[assignment]
    assert evaluate(runner).disposition is ExternalMetricDisposition.ERROR


def test_non_completed_trace_is_inconclusive_and_skips_runner() -> None:
    runner = FakeRunner()
    abstained = replace(
        trace(),
        status=EvaluationExecutionStatus.ABSTAINED,
        output_text=None,
        latency_ms=None,
    )
    result = evaluate_deepeval_metric(
        trace=abstained,
        input_text="Question",
        expected_output="Expected",
        context=("Context",),
        runner=runner,
        config=config(),
    )
    assert result.disposition is ExternalMetricDisposition.INCONCLUSIVE
    assert runner.requests == []


def test_metric_result_id_is_stable() -> None:
    assert evaluate(FakeRunner()).metric_result_id == evaluate(FakeRunner()).metric_result_id


def test_metrics_are_ordered_deterministically() -> None:
    metrics = (
        (config(metric_name="Z_METRIC"), FakeRunner()),
        (config(metric_name="A_METRIC"), FakeRunner()),
    )
    results = evaluate_deepeval_metrics(
        trace=trace(),
        input_text="Question",
        expected_output="Expected",
        context=("Context",),
        metrics=metrics,
    )
    assert [item.metric_name for item in results] == ["A_METRIC", "Z_METRIC"]


def test_duplicate_metric_configuration_is_rejected() -> None:
    with pytest.raises(DeepEvalAdvisoryError, match="duplicate metric configuration"):
        evaluate_deepeval_metrics(
            trace=trace(),
            input_text="Question",
            expected_output="Expected",
            context=("Context",),
            metrics=((config(), FakeRunner()), (config(), FakeRunner())),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"metric_name": ""},
        {"metric_version": ""},
        {"threshold": -0.1},
        {"threshold": 1.1},
        {"timeout_seconds": 0},
        {"judge_model": ""},
    ],
)
def test_invalid_config_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(DeepEvalAdvisoryError):
        config(**changes)


def test_request_requires_all_controlled_inputs() -> None:
    with pytest.raises(DeepEvalAdvisoryError):
        DeepEvalMetricRequest("", "expected", "actual", ("context",), 1)
    with pytest.raises(DeepEvalAdvisoryError):
        DeepEvalMetricRequest("input", "expected", "actual", (), 1)
