"""Bounded DeepEval-compatible advisory boundary for MO-022F.6.

This module defines an offline, injectable adapter for metric experiments. It
does not import DeepEval, call judge models, or override deterministic results.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import perf_counter
from typing import Protocol, runtime_checkable

from insurance_intelligence.contracts.llm_evaluation import (
    ExternalMetricDisposition,
    ExternalMetricResult,
    ModelExecutionTrace,
)


class DeepEvalAdvisoryError(ValueError):
    """Raised when bounded DeepEval configuration or input is invalid."""


class DeepEvalDependencyUnavailable(RuntimeError):
    """Raised when the optional metric implementation is unavailable."""


class DeepEvalMetricTimeout(TimeoutError):
    """Raised when metric execution exceeds its controlled timeout."""


class DeepEvalMetricError(RuntimeError):
    """Raised when a metric runner fails or returns an invalid result."""


@dataclass(frozen=True)
class DeepEvalMetricRequest:
    input_text: str
    expected_output: str
    actual_output: str
    context: tuple[str, ...]
    timeout_seconds: float

    def __post_init__(self) -> None:
        for field_name in ("input_text", "expected_output", "actual_output"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DeepEvalAdvisoryError(f"{field_name} must be non-empty text")
        if not isinstance(self.context, tuple) or not self.context:
            raise DeepEvalAdvisoryError("context must be a non-empty tuple")
        if not all(isinstance(item, str) and item.strip() for item in self.context):
            raise DeepEvalAdvisoryError("context must contain non-empty text values")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise DeepEvalAdvisoryError("timeout_seconds must be numeric")
        if float(self.timeout_seconds) <= 0:
            raise DeepEvalAdvisoryError("timeout_seconds must be greater than zero")


@runtime_checkable
class DeepEvalMetricRunner(Protocol):
    """Minimal injectable boundary implemented by real or fake metric runners."""

    def measure(self, request: DeepEvalMetricRequest) -> float:
        """Return a normalized metric score from 0.0 to 1.0."""


@dataclass(frozen=True)
class DeepEvalMetricConfig:
    metric_name: str
    metric_version: str
    threshold: float
    timeout_seconds: float
    judge_model: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("metric_name", "metric_version"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise DeepEvalAdvisoryError(f"{field_name} must be non-empty text")
        if self.judge_model is not None and (
            not isinstance(self.judge_model, str) or not self.judge_model.strip()
        ):
            raise DeepEvalAdvisoryError("judge_model must be non-empty text when provided")
        for field_name in ("threshold", "timeout_seconds"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise DeepEvalAdvisoryError(f"{field_name} must be numeric")
        if not 0.0 <= float(self.threshold) <= 1.0:
            raise DeepEvalAdvisoryError("threshold must be between 0 and 1")
        if float(self.timeout_seconds) <= 0:
            raise DeepEvalAdvisoryError("timeout_seconds must be greater than zero")


def _metric_result_id(
    trace: ModelExecutionTrace, config: DeepEvalMetricConfig
) -> str:
    payload = "|".join(
        (trace.case_id, trace.trace_id, config.metric_name, config.metric_version)
    )
    return f"deepeval_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _metric_version(config: DeepEvalMetricConfig) -> str:
    if config.judge_model is None:
        return config.metric_version
    return f"{config.metric_version}@{config.judge_model}"


def evaluate_deepeval_metric(
    *,
    trace: ModelExecutionTrace,
    input_text: str,
    expected_output: str,
    context: tuple[str, ...],
    runner: DeepEvalMetricRunner,
    config: DeepEvalMetricConfig,
) -> ExternalMetricResult:
    """Return one advisory metric result without changing deterministic authority."""
    if not isinstance(trace, ModelExecutionTrace):
        raise DeepEvalAdvisoryError("trace must be a ModelExecutionTrace")
    if not isinstance(config, DeepEvalMetricConfig):
        raise DeepEvalAdvisoryError("config must be a DeepEvalMetricConfig")
    if not isinstance(runner, DeepEvalMetricRunner):
        raise DeepEvalAdvisoryError("runner must implement DeepEvalMetricRunner")

    result_id = _metric_result_id(trace, config)
    version = _metric_version(config)

    if trace.output_text is None:
        return ExternalMetricResult(
            metric_result_id=result_id,
            case_id=trace.case_id,
            trace_id=trace.trace_id,
            metric_name=config.metric_name,
            metric_version=version,
            disposition=ExternalMetricDisposition.INCONCLUSIVE,
            rationale=(
                "DeepEval advisory evaluation requires a completed trace with output text.",
                "No deterministic verdict was changed.",
            ),
            threshold=float(config.threshold),
        )

    request = DeepEvalMetricRequest(
        input_text=input_text,
        expected_output=expected_output,
        actual_output=trace.output_text,
        context=context,
        timeout_seconds=float(config.timeout_seconds),
    )
    started = perf_counter()
    try:
        raw_score = runner.measure(request)
        elapsed = perf_counter() - started
        if elapsed > config.timeout_seconds:
            raise DeepEvalMetricTimeout(
                "DeepEval metric execution exceeded configured timeout"
            )
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise DeepEvalMetricError("DeepEval runner returned a non-numeric score")
        score = float(raw_score)
        if not 0.0 <= score <= 1.0:
            raise DeepEvalMetricError("DeepEval runner returned a score outside 0..1")
    except (
        DeepEvalDependencyUnavailable,
        DeepEvalMetricTimeout,
        DeepEvalMetricError,
    ) as exc:
        return ExternalMetricResult(
            metric_result_id=result_id,
            case_id=trace.case_id,
            trace_id=trace.trace_id,
            metric_name=config.metric_name,
            metric_version=version,
            disposition=ExternalMetricDisposition.ERROR,
            rationale=(
                f"DeepEval advisory metric failed: {type(exc).__name__}.",
                "No deterministic verdict was changed.",
            ),
            threshold=float(config.threshold),
            error_message=str(exc),
        )
    except Exception as exc:  # fail closed at the adapter boundary
        return ExternalMetricResult(
            metric_result_id=result_id,
            case_id=trace.case_id,
            trace_id=trace.trace_id,
            metric_name=config.metric_name,
            metric_version=version,
            disposition=ExternalMetricDisposition.ERROR,
            rationale=(
                "DeepEval advisory metric failed with an unexpected evaluation error.",
                "No deterministic verdict was changed.",
            ),
            threshold=float(config.threshold),
            error_message=f"{type(exc).__name__}: {exc}",
        )

    disposition = (
        ExternalMetricDisposition.SUPPORTS
        if score >= config.threshold
        else ExternalMetricDisposition.FLAGS
    )
    comparison = (
        "met or exceeded"
        if disposition is ExternalMetricDisposition.SUPPORTS
        else "fell below"
    )
    return ExternalMetricResult(
        metric_result_id=result_id,
        case_id=trace.case_id,
        trace_id=trace.trace_id,
        metric_name=config.metric_name,
        metric_version=version,
        disposition=disposition,
        rationale=(
            f"DeepEval metric score {score:.4f} {comparison} advisory threshold {config.threshold:.4f}.",
            "This result is advisory and does not override deterministic findings.",
        ),
        score=score,
        threshold=float(config.threshold),
    )


def evaluate_deepeval_metrics(
    *,
    trace: ModelExecutionTrace,
    input_text: str,
    expected_output: str,
    context: tuple[str, ...],
    metrics: tuple[tuple[DeepEvalMetricConfig, DeepEvalMetricRunner], ...],
) -> tuple[ExternalMetricResult, ...]:
    """Evaluate unique metrics in stable name/version order."""
    seen: set[tuple[str, str]] = set()
    ordered = sorted(
        metrics, key=lambda item: (item[0].metric_name, item[0].metric_version)
    )
    results: list[ExternalMetricResult] = []
    for config, runner in ordered:
        key = (config.metric_name, config.metric_version)
        if key in seen:
            raise DeepEvalAdvisoryError(
                f"duplicate metric configuration: {config.metric_name}@{config.metric_version}"
            )
        seen.add(key)
        results.append(
            evaluate_deepeval_metric(
                trace=trace,
                input_text=input_text,
                expected_output=expected_output,
                context=context,
                runner=runner,
                config=config,
            )
        )
    return tuple(results)
