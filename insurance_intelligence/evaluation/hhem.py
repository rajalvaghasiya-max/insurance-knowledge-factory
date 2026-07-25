"""Advisory HHEM evaluation boundary for MO-022F.5.

This module records hallucination-risk scores as external advisory evidence. It
never overrides deterministic evaluation results and does not download or load a
model automatically.
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


class HHEMAdvisoryError(ValueError):
    """Raised when HHEM advisory configuration or input is invalid."""


class HHEMModelUnavailable(RuntimeError):
    """Raised when the configured HHEM model cannot be used."""


class HHEMInferenceTimeout(TimeoutError):
    """Raised when HHEM inference exceeds its controlled timeout."""


class HHEMInferenceError(RuntimeError):
    """Raised when HHEM inference fails."""


@dataclass(frozen=True)
class HHEMScoreRequest:
    evidence_text: str
    candidate_text: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_text, str) or not self.evidence_text.strip():
            raise HHEMAdvisoryError("evidence_text must be non-empty text")
        if not isinstance(self.candidate_text, str) or not self.candidate_text.strip():
            raise HHEMAdvisoryError("candidate_text must be non-empty text")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise HHEMAdvisoryError("timeout_seconds must be numeric")
        if float(self.timeout_seconds) <= 0:
            raise HHEMAdvisoryError("timeout_seconds must be greater than zero")


@runtime_checkable
class HHEMScorer(Protocol):
    """Minimal injectable boundary implemented by a real or fake HHEM scorer."""

    def score(self, request: HHEMScoreRequest) -> float:
        """Return a groundedness score from 0.0 to 1.0."""


@dataclass(frozen=True)
class HHEMAdvisoryConfig:
    model_name: str
    model_version: str
    threshold: float
    timeout_seconds: float
    metric_name: str = "HHEM_GROUNDEDNESS_ADVISORY"

    def __post_init__(self) -> None:
        for field_name in ("model_name", "model_version", "metric_name"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise HHEMAdvisoryError(f"{field_name} must be non-empty text")
        for field_name in ("threshold", "timeout_seconds"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise HHEMAdvisoryError(f"{field_name} must be numeric")
        if not 0.0 <= float(self.threshold) <= 1.0:
            raise HHEMAdvisoryError("threshold must be between 0 and 1")
        if float(self.timeout_seconds) <= 0:
            raise HHEMAdvisoryError("timeout_seconds must be greater than zero")


def _metric_result_id(trace: ModelExecutionTrace, config: HHEMAdvisoryConfig) -> str:
    payload = "|".join(
        (trace.case_id, trace.trace_id, config.metric_name, config.model_version)
    )
    return f"hhem_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def evaluate_hhem_advisory(
    *,
    trace: ModelExecutionTrace,
    evidence_text: str,
    scorer: HHEMScorer,
    config: HHEMAdvisoryConfig,
) -> ExternalMetricResult:
    """Return one advisory metric result without changing deterministic authority."""
    if not isinstance(trace, ModelExecutionTrace):
        raise HHEMAdvisoryError("trace must be a ModelExecutionTrace")
    if not isinstance(config, HHEMAdvisoryConfig):
        raise HHEMAdvisoryError("config must be an HHEMAdvisoryConfig")
    if not isinstance(scorer, HHEMScorer):
        raise HHEMAdvisoryError("scorer must implement HHEMScorer")

    result_id = _metric_result_id(trace, config)
    metric_version = f"{config.model_name}@{config.model_version}"

    if trace.output_text is None:
        return ExternalMetricResult(
            metric_result_id=result_id,
            case_id=trace.case_id,
            trace_id=trace.trace_id,
            metric_name=config.metric_name,
            metric_version=metric_version,
            disposition=ExternalMetricDisposition.INCONCLUSIVE,
            rationale=(
                "HHEM advisory evaluation requires a completed trace with output text.",
                "No deterministic verdict was changed.",
            ),
            threshold=float(config.threshold),
        )

    request = HHEMScoreRequest(
        evidence_text=evidence_text,
        candidate_text=trace.output_text,
        timeout_seconds=float(config.timeout_seconds),
    )
    started = perf_counter()
    try:
        raw_score = scorer.score(request)
        elapsed = perf_counter() - started
        if elapsed > config.timeout_seconds:
            raise HHEMInferenceTimeout("HHEM inference exceeded configured timeout")
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise HHEMInferenceError("HHEM scorer returned a non-numeric score")
        score = float(raw_score)
        if not 0.0 <= score <= 1.0:
            raise HHEMInferenceError("HHEM scorer returned a score outside 0..1")
    except (HHEMModelUnavailable, HHEMInferenceTimeout, HHEMInferenceError) as exc:
        return ExternalMetricResult(
            metric_result_id=result_id,
            case_id=trace.case_id,
            trace_id=trace.trace_id,
            metric_name=config.metric_name,
            metric_version=metric_version,
            disposition=ExternalMetricDisposition.ERROR,
            rationale=(
                f"HHEM advisory evaluation failed: {type(exc).__name__}.",
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
            metric_version=metric_version,
            disposition=ExternalMetricDisposition.ERROR,
            rationale=(
                "HHEM advisory evaluation failed with an unexpected inference error.",
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
    comparison = "met or exceeded" if disposition is ExternalMetricDisposition.SUPPORTS else "fell below"
    return ExternalMetricResult(
        metric_result_id=result_id,
        case_id=trace.case_id,
        trace_id=trace.trace_id,
        metric_name=config.metric_name,
        metric_version=metric_version,
        disposition=disposition,
        rationale=(
            f"HHEM groundedness score {score:.4f} {comparison} advisory threshold {config.threshold:.4f}.",
            "This result is advisory and does not override deterministic findings.",
        ),
        score=score,
        threshold=float(config.threshold),
    )


def evaluate_hhem_batch(
    *,
    items: tuple[tuple[ModelExecutionTrace, str], ...],
    scorer: HHEMScorer,
    config: HHEMAdvisoryConfig,
) -> tuple[ExternalMetricResult, ...]:
    """Evaluate unique traces in stable case/trace order."""
    seen: set[str] = set()
    ordered = sorted(items, key=lambda item: (item[0].case_id, item[0].trace_id))
    results: list[ExternalMetricResult] = []
    for trace, evidence_text in ordered:
        if trace.trace_id in seen:
            raise HHEMAdvisoryError(f"duplicate trace_id: {trace.trace_id}")
        seen.add(trace.trace_id)
        results.append(
            evaluate_hhem_advisory(
                trace=trace,
                evidence_text=evidence_text,
                scorer=scorer,
                config=config,
            )
        )
    return tuple(results)
