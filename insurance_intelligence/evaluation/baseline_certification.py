"""Dataset-level deterministic baseline certification for MO-022F.

This module evaluates only byte-preserved reference outputs already stored in the
controlled dataset. Cases without a reference output remain explicitly
UNMATERIALIZED; they are never synthesized or silently counted as passing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256

from insurance_intelligence.contracts.llm_evaluation import (
    DeterministicEvaluationResult,
    EvaluationExecutionStatus,
    EvaluationExpectedOutcome,
    EvaluationVerdict,
    ModelExecutionTrace,
)
from insurance_intelligence.evaluation.dataset import EvaluationDataset
from insurance_intelligence.evaluation.deterministic import DeterministicLLMEvaluator


class BaselineCertificationError(ValueError):
    """Raised when baseline certification inputs violate an invariant."""


class BaselineCaseStatus(str, Enum):
    ALIGNED = "ALIGNED"
    MISALIGNED = "MISALIGNED"
    UNMATERIALIZED = "UNMATERIALIZED"


class BaselineReportStatus(str, Enum):
    CERTIFIED = "CERTIFIED"
    FAILED = "FAILED"


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _expected_verdict(outcome: EvaluationExpectedOutcome) -> EvaluationVerdict:
    return {
        EvaluationExpectedOutcome.PASS: EvaluationVerdict.PASSED,
        EvaluationExpectedOutcome.FAIL: EvaluationVerdict.FAILED,
        EvaluationExpectedOutcome.REVIEW_REQUIRED: EvaluationVerdict.REQUIRES_REVIEW,
    }[outcome]


@dataclass(frozen=True)
class BaselineCaseCertification:
    case_id: str
    status: BaselineCaseStatus
    expected_outcome: EvaluationExpectedOutcome
    expected_verdict: EvaluationVerdict
    observed_verdict: EvaluationVerdict | None
    deterministic_result: DeterministicEvaluationResult | None


@dataclass(frozen=True)
class DeterministicBaselineCertificationReport:
    report_id: str
    dataset_id: str
    dataset_version: str
    status: BaselineReportStatus
    cases: tuple[BaselineCaseCertification, ...]
    total_case_count: int
    materialized_case_count: int
    aligned_case_count: int
    misaligned_case_count: int
    unmaterialized_case_count: int
    coverage_rate: float

    def __post_init__(self) -> None:
        if not self.cases:
            raise BaselineCertificationError("cases must not be empty")
        ids = tuple(item.case_id for item in self.cases)
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise BaselineCertificationError("cases must be unique and ordered by case_id")
        if self.total_case_count != len(self.cases):
            raise BaselineCertificationError("total_case_count must match cases")
        if self.materialized_case_count + self.unmaterialized_case_count != self.total_case_count:
            raise BaselineCertificationError("materialized and unmaterialized counts must cover all cases")
        if self.aligned_case_count + self.misaligned_case_count != self.materialized_case_count:
            raise BaselineCertificationError("aligned and misaligned counts must cover materialized cases")
        expected_status = (
            BaselineReportStatus.CERTIFIED
            if self.materialized_case_count > 0 and self.misaligned_case_count == 0
            else BaselineReportStatus.FAILED
        )
        if self.status is not expected_status:
            raise BaselineCertificationError("report status does not match certification counts")


def certify_deterministic_baseline(
    dataset: EvaluationDataset,
    *,
    evaluator: DeterministicLLMEvaluator | None = None,
) -> DeterministicBaselineCertificationReport:
    if not isinstance(dataset, EvaluationDataset):
        raise BaselineCertificationError("dataset must be an EvaluationDataset")
    resolved_evaluator = evaluator or DeterministicLLMEvaluator()
    if not isinstance(resolved_evaluator, DeterministicLLMEvaluator):
        raise BaselineCertificationError("evaluator must be a DeterministicLLMEvaluator")

    certifications: list[BaselineCaseCertification] = []
    for case in dataset.cases:
        expected = _expected_verdict(case.expected_outcome)
        if case.reference_output is None:
            certifications.append(
                BaselineCaseCertification(
                    case_id=case.case_id,
                    status=BaselineCaseStatus.UNMATERIALIZED,
                    expected_outcome=case.expected_outcome,
                    expected_verdict=expected,
                    observed_verdict=None,
                    deterministic_result=None,
                )
            )
            continue

        trace = ModelExecutionTrace(
            trace_id=f"baseline-reference-{case.case_id}",
            input_id=f"baseline-input-{case.case_id}",
            case_id=case.case_id,
            provider="CONTROLLED_DATASET",
            model="REFERENCE_OUTPUT",
            model_version=dataset.dataset_version,
            prompt_version="REFERENCE_OUTPUT_V1",
            parameters=(),
            run_number=1,
            status=EvaluationExecutionStatus.COMPLETED,
            output_text=case.reference_output,
        )
        result = resolved_evaluator.evaluate(case, trace)
        aligned = result.verdict is expected
        certifications.append(
            BaselineCaseCertification(
                case_id=case.case_id,
                status=BaselineCaseStatus.ALIGNED if aligned else BaselineCaseStatus.MISALIGNED,
                expected_outcome=case.expected_outcome,
                expected_verdict=expected,
                observed_verdict=result.verdict,
                deterministic_result=result,
            )
        )

    ordered = tuple(sorted(certifications, key=lambda item: item.case_id))
    materialized = sum(item.status is not BaselineCaseStatus.UNMATERIALIZED for item in ordered)
    aligned = sum(item.status is BaselineCaseStatus.ALIGNED for item in ordered)
    misaligned = sum(item.status is BaselineCaseStatus.MISALIGNED for item in ordered)
    unmaterialized = sum(item.status is BaselineCaseStatus.UNMATERIALIZED for item in ordered)
    status = (
        BaselineReportStatus.CERTIFIED
        if materialized > 0 and misaligned == 0
        else BaselineReportStatus.FAILED
    )
    signature = tuple((item.case_id, item.status.value, item.observed_verdict) for item in ordered)
    return DeterministicBaselineCertificationReport(
        report_id=_stable_id("deterministic-baseline", dataset.dataset_id, dataset.dataset_version, signature),
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        status=status,
        cases=ordered,
        total_case_count=len(ordered),
        materialized_case_count=materialized,
        aligned_case_count=aligned,
        misaligned_case_count=misaligned,
        unmaterialized_case_count=unmaterialized,
        coverage_rate=round(materialized / len(ordered), 4),
    )


__all__ = [
    "BaselineCaseCertification",
    "BaselineCaseStatus",
    "BaselineCertificationError",
    "BaselineReportStatus",
    "DeterministicBaselineCertificationReport",
    "certify_deterministic_baseline",
]
