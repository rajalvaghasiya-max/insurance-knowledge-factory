from pathlib import Path

import pytest

from insurance_intelligence.evaluation.baseline_certification import (
    BaselineCaseStatus,
    BaselineCertificationError,
    BaselineReportStatus,
    certify_deterministic_baseline,
)
from insurance_intelligence.evaluation.dataset import load_evaluation_dataset


FIXTURES = Path("tests/fixtures/insurance_intelligence/llm_evaluation")


def _report():
    return certify_deterministic_baseline(load_evaluation_dataset(FIXTURES))


def test_controlled_dataset_baseline_is_certified():
    report = _report()
    assert report.status is BaselineReportStatus.CERTIFIED
    assert report.total_case_count == 24
    assert report.materialized_case_count > 0
    assert report.aligned_case_count == report.materialized_case_count
    assert report.misaligned_case_count == 0
    assert report.unmaterialized_case_count > 0
    assert 0.0 < report.coverage_rate < 1.0


def test_cases_are_deterministically_ordered():
    ids = tuple(item.case_id for item in _report().cases)
    assert ids == tuple(sorted(ids))


def test_known_good_star_reference_passes():
    case = next(item for item in _report().cases if item.case_id == "kg-001")
    assert case.status is BaselineCaseStatus.ALIGNED
    assert case.expected_verdict.value == "PASSED"
    assert case.observed_verdict.value == "PASSED"
    assert case.deterministic_result is not None


def test_known_bad_malformed_condition_fails_as_expected():
    case = next(item for item in _report().cases if item.case_id == "kb-001")
    assert case.status is BaselineCaseStatus.ALIGNED
    assert case.expected_verdict.value == "FAILED"
    assert case.observed_verdict.value == "FAILED"
    assert "MISSING_CONDITION" in case.deterministic_result.failure_codes


def test_known_bad_percentage_change_fails_as_expected():
    case = next(item for item in _report().cases if item.case_id == "kb-004")
    assert case.status is BaselineCaseStatus.ALIGNED
    assert "NUMERICAL_ALTERATION" in case.deterministic_result.failure_codes


def test_unmaterialized_cases_are_not_synthesized_or_counted_as_passes():
    case = next(item for item in _report().cases if item.case_id == "kg-002")
    assert case.status is BaselineCaseStatus.UNMATERIALIZED
    assert case.observed_verdict is None
    assert case.deterministic_result is None


def test_report_is_reproducible():
    assert _report() == _report()


def test_rejects_wrong_dataset_type():
    with pytest.raises(BaselineCertificationError, match="EvaluationDataset"):
        certify_deterministic_baseline(object())
