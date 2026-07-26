"""Deterministic versus external-metric disagreement analysis for MO-022F.7.

This module classifies agreement and disagreement records only. It never changes
a deterministic verdict, reruns an evaluator, or approves an LLM responsibility.
"""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationDisagreement,
    EvaluationDisagreementCategory,
    EvaluationVerdict,
    ExternalMetricDisposition,
    ExternalMetricResult,
)


class EvaluationDisagreementError(ValueError):
    """Raised when disagreement-analysis inputs violate identity invariants."""


def _disagreement_id(deterministic_result: DeterministicEvaluationResult, external_metric_result: ExternalMetricResult) -> str:
    payload = "|".join((deterministic_result.result_id, external_metric_result.metric_result_id, deterministic_result.case_id, deterministic_result.trace_id))
    return f"disagreement_{sha256(payload.encode('utf-8')).hexdigest()[:20]}"


def _classify(deterministic_verdict: EvaluationVerdict, external_disposition: ExternalMetricDisposition) -> EvaluationDisagreementCategory:
    if deterministic_verdict is EvaluationVerdict.PASSED:
        if external_disposition is ExternalMetricDisposition.SUPPORTS:
            return EvaluationDisagreementCategory.BOTH_PASS
        if external_disposition is ExternalMetricDisposition.FLAGS:
            return EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL
        return EvaluationDisagreementCategory.INCONCLUSIVE
    if deterministic_verdict is EvaluationVerdict.FAILED:
        if external_disposition is ExternalMetricDisposition.SUPPORTS:
            return EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS
        if external_disposition is ExternalMetricDisposition.FLAGS:
            return EvaluationDisagreementCategory.BOTH_FAIL
        return EvaluationDisagreementCategory.INCONCLUSIVE
    return EvaluationDisagreementCategory.INCONCLUSIVE


def _rationale(*, deterministic_result: DeterministicEvaluationResult, external_metric_result: ExternalMetricResult, category: EvaluationDisagreementCategory) -> tuple[str, ...]:
    lines = [
        f"Deterministic verdict {deterministic_result.verdict.value} was compared with external metric {external_metric_result.metric_name} disposition {external_metric_result.disposition.value}.",
        f"Comparison category: {category.value}.",
        "The deterministic verdict remains unchanged and authoritative.",
    ]
    if deterministic_result.failure_codes:
        lines.append("Deterministic failure codes: " + ", ".join(sorted(deterministic_result.failure_codes)) + ".")
    if external_metric_result.score is not None:
        threshold = f" against threshold {external_metric_result.threshold:.4f}" if external_metric_result.threshold is not None else ""
        lines.append(f"External metric score: {external_metric_result.score:.4f}{threshold}.")
    if external_metric_result.disposition is ExternalMetricDisposition.ERROR:
        lines.append("External metric execution failed; its result cannot support an authority decision.")
    elif external_metric_result.disposition is ExternalMetricDisposition.INCONCLUSIVE:
        lines.append("External metric evidence was inconclusive and requires cautious interpretation.")
    return tuple(lines)


def analyze_evaluation_disagreement(*, deterministic_result: DeterministicEvaluationResult, external_metric_result: ExternalMetricResult) -> EvaluationDisagreement:
    """Create one immutable comparison record without changing either input."""
    if not isinstance(deterministic_result, DeterministicEvaluationResult):
        raise EvaluationDisagreementError("deterministic_result must be a DeterministicEvaluationResult")
    if not isinstance(external_metric_result, ExternalMetricResult):
        raise EvaluationDisagreementError("external_metric_result must be an ExternalMetricResult")
    if deterministic_result.case_id != external_metric_result.case_id:
        raise EvaluationDisagreementError("deterministic and external metric case_id values must match")
    if deterministic_result.trace_id != external_metric_result.trace_id:
        raise EvaluationDisagreementError("deterministic and external metric trace_id values must match")
    category = _classify(deterministic_result.verdict, external_metric_result.disposition)
    review_required = category in {
        EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
        EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL,
        EvaluationDisagreementCategory.INCONCLUSIVE,
    }
    return EvaluationDisagreement(
        disagreement_id=_disagreement_id(deterministic_result, external_metric_result),
        case_id=deterministic_result.case_id,
        trace_id=deterministic_result.trace_id,
        deterministic_result_id=deterministic_result.result_id,
        external_metric_result_id=external_metric_result.metric_result_id,
        category=category,
        rationale=_rationale(deterministic_result=deterministic_result, external_metric_result=external_metric_result, category=category),
        review_required=review_required,
    )


def analyze_evaluation_disagreements(*, items: tuple[tuple[DeterministicEvaluationResult, ExternalMetricResult], ...]) -> tuple[EvaluationDisagreement, ...]:
    """Analyze unique metric results in deterministic case/trace/metric order."""
    if not isinstance(items, tuple):
        raise EvaluationDisagreementError("items must be a tuple")
    ordered = sorted(items, key=lambda item: (item[0].case_id, item[0].trace_id, item[1].metric_name, item[1].metric_result_id))
    seen_metric_ids: set[str] = set(); results: list[EvaluationDisagreement] = []
    for deterministic_result, external_metric_result in ordered:
        if external_metric_result.metric_result_id in seen_metric_ids:
            raise EvaluationDisagreementError(f"duplicate external metric result ID: {external_metric_result.metric_result_id}")
        seen_metric_ids.add(external_metric_result.metric_result_id)
        results.append(analyze_evaluation_disagreement(deterministic_result=deterministic_result, external_metric_result=external_metric_result))
    return tuple(results)
