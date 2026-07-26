from __future__ import annotations

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationDisagreementCategory,
    EvaluationVerdict,
    ExternalMetricDisposition,
    ExternalMetricResult,
)
from insurance_intelligence.evaluation.disagreement import (
    EvaluationDisagreementError,
    analyze_evaluation_disagreement,
    analyze_evaluation_disagreements,
)


def deterministic(verdict: EvaluationVerdict = EvaluationVerdict.PASSED, *, case_id: str = "case-a", trace_id: str = "trace-a", result_id: str = "det-a") -> DeterministicEvaluationResult:
    failed = ("check-failed",) if verdict is EvaluationVerdict.FAILED else ()
    codes = ("UNSUPPORTED_FACT",) if verdict is EvaluationVerdict.FAILED else ()
    return DeterministicEvaluationResult(result_id=result_id, case_id=case_id, trace_id=trace_id, verdict=verdict, passed_check_ids=("check-passed",) if verdict is EvaluationVerdict.PASSED else (), failed_check_ids=failed, failure_codes=codes)


def external(disposition: ExternalMetricDisposition = ExternalMetricDisposition.SUPPORTS, *, case_id: str = "case-a", trace_id: str = "trace-a", metric_result_id: str = "metric-a", metric_name: str = "HHEM") -> ExternalMetricResult:
    score = 0.9 if disposition is ExternalMetricDisposition.SUPPORTS else None
    if disposition is ExternalMetricDisposition.FLAGS:
        score = 0.2
    return ExternalMetricResult(metric_result_id=metric_result_id, case_id=case_id, trace_id=trace_id, metric_name=metric_name, metric_version="1", disposition=disposition, rationale=("advisory result",), score=score, threshold=0.8, error_message="metric unavailable" if disposition is ExternalMetricDisposition.ERROR else None)


@pytest.mark.parametrize(("verdict", "disposition", "category", "review_required"), [
    (EvaluationVerdict.PASSED, ExternalMetricDisposition.SUPPORTS, EvaluationDisagreementCategory.BOTH_PASS, False),
    (EvaluationVerdict.FAILED, ExternalMetricDisposition.FLAGS, EvaluationDisagreementCategory.BOTH_FAIL, False),
    (EvaluationVerdict.FAILED, ExternalMetricDisposition.SUPPORTS, EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS, True),
    (EvaluationVerdict.PASSED, ExternalMetricDisposition.FLAGS, EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL, True),
])
def test_classifies_conclusive_comparisons(verdict, disposition, category, review_required):
    result = analyze_evaluation_disagreement(deterministic_result=deterministic(verdict), external_metric_result=external(disposition))
    assert result.category is category
    assert result.review_required is review_required


@pytest.mark.parametrize("verdict", [EvaluationVerdict.REQUIRES_REVIEW, EvaluationVerdict.NOT_EVALUATED])
def test_non_conclusive_deterministic_verdict_is_inconclusive(verdict):
    result = analyze_evaluation_disagreement(deterministic_result=deterministic(verdict), external_metric_result=external())
    assert result.category is EvaluationDisagreementCategory.INCONCLUSIVE
    assert result.review_required is True


@pytest.mark.parametrize("disposition", [ExternalMetricDisposition.INCONCLUSIVE, ExternalMetricDisposition.ERROR])
def test_non_conclusive_external_metric_is_inconclusive(disposition):
    result = analyze_evaluation_disagreement(deterministic_result=deterministic(), external_metric_result=external(disposition))
    assert result.category is EvaluationDisagreementCategory.INCONCLUSIVE
    assert result.review_required is True


def test_analysis_preserves_input_identity_and_authority():
    det = deterministic(EvaluationVerdict.FAILED); metric = external(ExternalMetricDisposition.SUPPORTS)
    result = analyze_evaluation_disagreement(deterministic_result=det, external_metric_result=metric)
    assert result.deterministic_result_id == det.result_id
    assert result.external_metric_result_id == metric.metric_result_id
    assert result.case_id == det.case_id and result.trace_id == det.trace_id
    assert det.verdict is EvaluationVerdict.FAILED
    assert "remains unchanged and authoritative" in result.rationale[2]


def test_rationale_records_failure_codes_and_score():
    result = analyze_evaluation_disagreement(deterministic_result=deterministic(EvaluationVerdict.FAILED), external_metric_result=external())
    assert any("UNSUPPORTED_FACT" in line for line in result.rationale)
    assert any("0.9000" in line for line in result.rationale)


def test_error_metric_rationale_records_execution_failure():
    result = analyze_evaluation_disagreement(deterministic_result=deterministic(), external_metric_result=external(ExternalMetricDisposition.ERROR))
    assert any("execution failed" in line for line in result.rationale)


def test_disagreement_id_is_stable():
    first = analyze_evaluation_disagreement(deterministic_result=deterministic(), external_metric_result=external())
    second = analyze_evaluation_disagreement(deterministic_result=deterministic(), external_metric_result=external())
    assert first.disagreement_id == second.disagreement_id


def test_mismatched_case_id_is_rejected():
    with pytest.raises(EvaluationDisagreementError, match="case_id"):
        analyze_evaluation_disagreement(deterministic_result=deterministic(case_id="case-a"), external_metric_result=external(case_id="case-b"))


def test_mismatched_trace_id_is_rejected():
    with pytest.raises(EvaluationDisagreementError, match="trace_id"):
        analyze_evaluation_disagreement(deterministic_result=deterministic(trace_id="trace-a"), external_metric_result=external(trace_id="trace-b"))


def test_batch_order_is_deterministic_by_case_trace_and_metric():
    result = analyze_evaluation_disagreements(items=(
        (deterministic(case_id="case-z", trace_id="trace-z", result_id="det-z"), external(case_id="case-z", trace_id="trace-z", metric_result_id="metric-z", metric_name="HHEM")),
        (deterministic(case_id="case-a", trace_id="trace-a", result_id="det-a"), external(case_id="case-a", trace_id="trace-a", metric_result_id="metric-b", metric_name="HHEM")),
        (deterministic(case_id="case-a", trace_id="trace-a", result_id="det-a"), external(case_id="case-a", trace_id="trace-a", metric_result_id="metric-a", metric_name="DEEPEVAL")),
    ))
    assert [item.external_metric_result_id for item in result] == ["metric-a", "metric-b", "metric-z"]


def test_batch_rejects_duplicate_external_metric_result_ids():
    pair = (deterministic(), external())
    with pytest.raises(EvaluationDisagreementError, match="duplicate"):
        analyze_evaluation_disagreements(items=(pair, pair))


def test_batch_requires_tuple():
    with pytest.raises(EvaluationDisagreementError, match="tuple"):
        analyze_evaluation_disagreements(items=[])  # type: ignore[arg-type]


def test_invalid_input_types_are_rejected():
    with pytest.raises(EvaluationDisagreementError, match="deterministic_result"):
        analyze_evaluation_disagreement(deterministic_result="bad", external_metric_result=external())  # type: ignore[arg-type]
    with pytest.raises(EvaluationDisagreementError, match="external_metric_result"):
        analyze_evaluation_disagreement(deterministic_result=deterministic(), external_metric_result="bad")  # type: ignore[arg-type]
