from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationExecutionStatus,
    ExternalMetricDisposition,
    ModelExecutionTrace,
)
from insurance_intelligence.evaluation.hhem import (
    HHEMAdvisoryConfig,
    HHEMAdvisoryError,
    HHEMInferenceError,
    HHEMInferenceTimeout,
    HHEMModelUnavailable,
    HHEMScoreRequest,
    evaluate_hhem_advisory,
    evaluate_hhem_batch,
)


class FakeScorer:
    def __init__(self, score: float = 0.9, error: Exception | None = None):
        self.result = score
        self.error = error
        self.requests: list[HHEMScoreRequest] = []

    def score(self, request: HHEMScoreRequest) -> float:
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.result


def trace(case_id: str = "case-b", trace_id: str = "trace-b") -> ModelExecutionTrace:
    return ModelExecutionTrace(
        trace_id=trace_id,
        input_id=f"input-{case_id}",
        case_id=case_id,
        provider="fake",
        model="fake-model",
        model_version="1",
        prompt_version="p1",
        parameters=(),
        run_number=1,
        status=EvaluationExecutionStatus.COMPLETED,
        output_text="The policy applies a 10% copayment when the stated condition is met.",
        latency_ms=1,
    )


def config(**changes: object) -> HHEMAdvisoryConfig:
    values = dict(
        model_name="vectara-hhem",
        model_version="2.1",
        threshold=0.8,
        timeout_seconds=2.0,
    )
    values.update(changes)
    return HHEMAdvisoryConfig(**values)


def test_supporting_score_is_advisory_and_records_identity() -> None:
    scorer = FakeScorer(0.91)
    result = evaluate_hhem_advisory(
        trace=trace(), evidence_text="A 10% copayment applies conditionally.", scorer=scorer, config=config()
    )
    assert result.disposition is ExternalMetricDisposition.SUPPORTS
    assert result.score == 0.91
    assert result.threshold == 0.8
    assert result.metric_version == "vectara-hhem@2.1"
    assert "does not override deterministic findings" in result.rationale[1]
    assert scorer.requests[0].timeout_seconds == 2.0


def test_below_threshold_flags_without_authoritative_failure() -> None:
    result = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=FakeScorer(0.2), config=config()
    )
    assert result.disposition is ExternalMetricDisposition.FLAGS
    assert result.score == 0.2
    assert "advisory" in result.rationale[1].lower()


@pytest.mark.parametrize(
    "error",
    [
        HHEMModelUnavailable("model unavailable"),
        HHEMInferenceTimeout("timed out"),
        HHEMInferenceError("inference failed"),
    ],
)
def test_controlled_failures_return_error_results(error: Exception) -> None:
    result = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=FakeScorer(error=error), config=config()
    )
    assert result.disposition is ExternalMetricDisposition.ERROR
    assert result.error_message == str(error)
    assert result.score is None


def test_unexpected_scorer_exception_fails_closed() -> None:
    result = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=FakeScorer(error=RuntimeError("boom")), config=config()
    )
    assert result.disposition is ExternalMetricDisposition.ERROR
    assert result.error_message == "RuntimeError: boom"


@pytest.mark.parametrize("score", [-0.1, 1.1, True, "bad"])
def test_invalid_scorer_output_is_recorded_as_error(score: object) -> None:
    scorer = FakeScorer()
    scorer.result = score  # type: ignore[assignment]
    result = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=scorer, config=config()
    )
    assert result.disposition is ExternalMetricDisposition.ERROR


def test_non_completed_trace_is_inconclusive_and_does_not_call_scorer() -> None:
    scorer = FakeScorer()
    abstained = replace(
        trace(),
        status=EvaluationExecutionStatus.ABSTAINED,
        output_text=None,
        latency_ms=None,
    )
    result = evaluate_hhem_advisory(
        trace=abstained, evidence_text="Evidence", scorer=scorer, config=config()
    )
    assert result.disposition is ExternalMetricDisposition.INCONCLUSIVE
    assert scorer.requests == []


def test_metric_result_id_is_stable() -> None:
    first = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=FakeScorer(), config=config()
    )
    second = evaluate_hhem_advisory(
        trace=trace(), evidence_text="Evidence", scorer=FakeScorer(), config=config()
    )
    assert first.metric_result_id == second.metric_result_id


def test_batch_order_is_deterministic() -> None:
    results = evaluate_hhem_batch(
        items=((trace("case-z", "trace-z"), "Z"), (trace("case-a", "trace-a"), "A")),
        scorer=FakeScorer(),
        config=config(),
    )
    assert [result.case_id for result in results] == ["case-a", "case-z"]


def test_batch_rejects_duplicate_trace_ids() -> None:
    with pytest.raises(HHEMAdvisoryError, match="duplicate trace_id"):
        evaluate_hhem_batch(
            items=((trace("case-a", "same"), "A"), (trace("case-b", "same"), "B")),
            scorer=FakeScorer(),
            config=config(),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"model_name": ""},
        {"model_version": ""},
        {"threshold": -0.1},
        {"threshold": 1.1},
        {"timeout_seconds": 0},
    ],
)
def test_invalid_config_is_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(HHEMAdvisoryError):
        config(**changes)


def test_request_requires_evidence_and_candidate_text() -> None:
    with pytest.raises(HHEMAdvisoryError):
        HHEMScoreRequest(evidence_text="", candidate_text="answer", timeout_seconds=1)
    with pytest.raises(HHEMAdvisoryError):
        HHEMScoreRequest(evidence_text="evidence", candidate_text="", timeout_seconds=1)
