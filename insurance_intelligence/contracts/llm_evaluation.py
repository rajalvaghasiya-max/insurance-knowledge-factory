"""Controlled LLM evaluation contracts for MO-022F.1.

These immutable contracts define evaluation cases, execution traces, deterministic
results, advisory external metrics, disagreement records, and bounded adoption
decisions. They intentionally do not call providers, calculate metric scores, or
approve LLM output for production use.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class LLMEvaluationContractError(ValueError):
    """Raised when a controlled-evaluation contract violates an invariant."""


class EvaluationCaseCategory(str, Enum):
    KNOWN_GOOD = "KNOWN_GOOD"
    KNOWN_BAD = "KNOWN_BAD"
    ADVERSARIAL = "ADVERSARIAL"
    HISTORICAL_REGRESSION = "HISTORICAL_REGRESSION"


class EvaluationExpectedOutcome(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class SemanticComponent(str, Enum):
    FACT = "FACT"
    EFFECT = "EFFECT"
    TRIGGER = "TRIGGER"
    EXCEPTION = "EXCEPTION"
    APPLICABILITY_SCOPE = "APPLICABILITY_SCOPE"
    LIMITATION = "LIMITATION"
    UNCERTAINTY = "UNCERTAINTY"
    EVIDENCE_REFERENCE = "EVIDENCE_REFERENCE"
    AUDIENCE = "AUDIENCE"


class ForbiddenBehaviour(str, Enum):
    UNSUPPORTED_FACT = "UNSUPPORTED_FACT"
    NUMERICAL_ALTERATION = "NUMERICAL_ALTERATION"
    MISSING_CONDITION = "MISSING_CONDITION"
    MISSING_EXCEPTION = "MISSING_EXCEPTION"
    MISSING_SCOPE = "MISSING_SCOPE"
    CERTAINTY_INFLATION = "CERTAINTY_INFLATION"
    FACT_IMPLICATION_CONFUSION = "FACT_IMPLICATION_CONFUSION"
    UNSUPPORTED_RECOMMENDATION = "UNSUPPORTED_RECOMMENDATION"
    CITATION_MISMATCH = "CITATION_MISMATCH"
    FAILURE_TO_ABSTAIN = "FAILURE_TO_ABSTAIN"
    CLAIM_PAYMENT_PREDICTION = "CLAIM_PAYMENT_PREDICTION"


class LLMResponsibility(str, Enum):
    PLAIN_LANGUAGE_REPHRASING = "PLAIN_LANGUAGE_REPHRASING"
    AUDIENCE_ADAPTATION = "AUDIENCE_ADAPTATION"
    EXPLANATION_ORDERING = "EXPLANATION_ORDERING"
    EXAMPLE_GENERATION = "EXAMPLE_GENERATION"
    FACT_EXTRACTION = "FACT_EXTRACTION"
    PRODUCT_IDENTITY = "PRODUCT_IDENTITY"
    NUMERICAL_CALCULATION = "NUMERICAL_CALCULATION"
    SOURCE_HIERARCHY = "SOURCE_HIERARCHY"
    CURRENTNESS_SELECTION = "CURRENTNESS_SELECTION"
    CONTRADICTION_RESOLUTION = "CONTRADICTION_RESOLUTION"
    SUITABILITY_RECOMMENDATION = "SUITABILITY_RECOMMENDATION"
    CLAIM_PAYMENT_PREDICTION = "CLAIM_PAYMENT_PREDICTION"


class EvaluationExecutionStatus(str, Enum):
    COMPLETED = "COMPLETED"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    TIMEOUT = "TIMEOUT"
    ABSTAINED = "ABSTAINED"


class EvaluationVerdict(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"
    NOT_EVALUATED = "NOT_EVALUATED"


class ExternalMetricDisposition(str, Enum):
    SUPPORTS = "SUPPORTS"
    FLAGS = "FLAGS"
    INCONCLUSIVE = "INCONCLUSIVE"
    ERROR = "ERROR"


class EvaluationDisagreementCategory(str, Enum):
    BOTH_PASS = "BOTH_PASS"
    DETERMINISTIC_FAIL_EXTERNAL_PASS = "DETERMINISTIC_FAIL_EXTERNAL_PASS"
    DETERMINISTIC_PASS_EXTERNAL_FAIL = "DETERMINISTIC_PASS_EXTERNAL_FAIL"
    BOTH_FAIL = "BOTH_FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class ResponsibilityDecisionStatus(str, Enum):
    APPROVED_FOR_CONTROLLED_USE = "APPROVED_FOR_CONTROLLED_USE"
    APPROVED_WITH_DETERMINISTIC_VALIDATION = "APPROVED_WITH_DETERMINISTIC_VALIDATION"
    EXPERIMENTAL_ONLY = "EXPERIMENTAL_ONLY"
    REJECTED = "REJECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LLMEvaluationContractError(f"{field_name} must be non-empty text")
    return value.strip()


def _optional_text(value: object, field_name: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field_name)


def _text_tuple(
    values: Iterable[str] | tuple[str, ...],
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[str, ...]:
    if isinstance(values, str):
        raise LLMEvaluationContractError(f"{field_name} must be a sequence of text values")
    normalised = tuple(_required_text(value, field_name) for value in values)
    if not allow_empty and not normalised:
        raise LLMEvaluationContractError(f"{field_name} must not be empty")
    if len(set(normalised)) != len(normalised):
        raise LLMEvaluationContractError(f"{field_name} must not contain duplicates")
    return normalised


def _typed_tuple(
    values: tuple[object, ...],
    expected_type: type,
    field_name: str,
    *,
    allow_empty: bool = True,
) -> tuple[object, ...]:
    if not isinstance(values, tuple):
        raise LLMEvaluationContractError(f"{field_name} must be a tuple")
    if not allow_empty and not values:
        raise LLMEvaluationContractError(f"{field_name} must not be empty")
    if not all(isinstance(item, expected_type) for item in values):
        raise LLMEvaluationContractError(
            f"{field_name} must contain {expected_type.__name__} values"
        )
    return values


def _enum(value: object, expected_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise LLMEvaluationContractError(
            f"{field_name} must be a {expected_type.__name__} value"
        )


def _score(value: object, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LLMEvaluationContractError(f"{field_name} must be numeric")
    score = float(value)
    if not 0.0 <= score <= 1.0:
        raise LLMEvaluationContractError(f"{field_name} must be between 0 and 1")
    return score


@dataclass(frozen=True)
class ExpectedSemanticRequirement:
    requirement_id: str
    component: SemanticComponent
    expected_text: str
    evidence_ids: tuple[str, ...]
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "requirement_id", _required_text(self.requirement_id, "requirement_id")
        )
        _enum(self.component, SemanticComponent, "component")
        object.__setattr__(
            self, "expected_text", _required_text(self.expected_text, "expected_text")
        )
        object.__setattr__(
            self,
            "evidence_ids",
            _text_tuple(self.evidence_ids, "evidence_ids", allow_empty=False),
        )
        if not isinstance(self.required, bool):
            raise LLMEvaluationContractError("required must be boolean")


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    title: str
    category: EvaluationCaseCategory
    responsibility: LLMResponsibility
    audience: str
    governed_evidence_ids: tuple[str, ...]
    approved_finding_ids: tuple[str, ...]
    semantic_requirements: tuple[ExpectedSemanticRequirement, ...]
    forbidden_behaviours: tuple[ForbiddenBehaviour, ...]
    expected_outcome: EvaluationExpectedOutcome
    reference_output: str | None = None
    historical_defect_id: str | None = None
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _required_text(self.case_id, "case_id"))
        object.__setattr__(self, "title", _required_text(self.title, "title"))
        _enum(self.category, EvaluationCaseCategory, "category")
        _enum(self.responsibility, LLMResponsibility, "responsibility")
        object.__setattr__(self, "audience", _required_text(self.audience, "audience"))
        object.__setattr__(
            self,
            "governed_evidence_ids",
            _text_tuple(
                self.governed_evidence_ids,
                "governed_evidence_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "approved_finding_ids",
            _text_tuple(
                self.approved_finding_ids,
                "approved_finding_ids",
                allow_empty=False,
            ),
        )
        _typed_tuple(
            self.semantic_requirements,
            ExpectedSemanticRequirement,
            "semantic_requirements",
            allow_empty=False,
        )
        requirement_ids = tuple(item.requirement_id for item in self.semantic_requirements)
        if len(set(requirement_ids)) != len(requirement_ids):
            raise LLMEvaluationContractError(
                "semantic_requirements must have unique requirement IDs"
            )
        if not isinstance(self.forbidden_behaviours, tuple):
            raise LLMEvaluationContractError("forbidden_behaviours must be a tuple")
        if not all(
            isinstance(item, ForbiddenBehaviour) for item in self.forbidden_behaviours
        ):
            raise LLMEvaluationContractError(
                "forbidden_behaviours must contain ForbiddenBehaviour values"
            )
        if len(set(self.forbidden_behaviours)) != len(self.forbidden_behaviours):
            raise LLMEvaluationContractError(
                "forbidden_behaviours must not contain duplicates"
            )
        _enum(self.expected_outcome, EvaluationExpectedOutcome, "expected_outcome")
        object.__setattr__(
            self,
            "reference_output",
            _optional_text(self.reference_output, "reference_output"),
        )
        object.__setattr__(
            self,
            "historical_defect_id",
            _optional_text(self.historical_defect_id, "historical_defect_id"),
        )
        object.__setattr__(self, "tags", _text_tuple(self.tags, "tags"))
        if (
            self.category is EvaluationCaseCategory.HISTORICAL_REGRESSION
            and self.historical_defect_id is None
        ):
            raise LLMEvaluationContractError(
                "historical regression cases require historical_defect_id"
            )


@dataclass(frozen=True)
class EvaluationInput:
    input_id: str
    case_id: str
    prompt_version: str
    governed_evidence_ids: tuple[str, ...]
    approved_finding_ids: tuple[str, ...]
    audience: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_id", _required_text(self.input_id, "input_id"))
        object.__setattr__(self, "case_id", _required_text(self.case_id, "case_id"))
        object.__setattr__(
            self, "prompt_version", _required_text(self.prompt_version, "prompt_version")
        )
        object.__setattr__(
            self,
            "governed_evidence_ids",
            _text_tuple(
                self.governed_evidence_ids,
                "governed_evidence_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(
            self,
            "approved_finding_ids",
            _text_tuple(
                self.approved_finding_ids,
                "approved_finding_ids",
                allow_empty=False,
            ),
        )
        object.__setattr__(self, "audience", _required_text(self.audience, "audience"))


@dataclass(frozen=True)
class ModelParameter:
    name: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "name"))
        object.__setattr__(self, "value", _required_text(self.value, "value"))


@dataclass(frozen=True)
class ModelExecutionTrace:
    trace_id: str
    input_id: str
    case_id: str
    provider: str
    model: str
    model_version: str
    prompt_version: str
    parameters: tuple[ModelParameter, ...]
    run_number: int
    status: EvaluationExecutionStatus
    output_text: str | None = None
    error_message: str | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "trace_id",
            "input_id",
            "case_id",
            "provider",
            "model",
            "model_version",
            "prompt_version",
        ):
            object.__setattr__(
                self, field_name, _required_text(getattr(self, field_name), field_name)
            )
        _typed_tuple(self.parameters, ModelParameter, "parameters")
        names = tuple(item.name for item in self.parameters)
        if len(set(names)) != len(names):
            raise LLMEvaluationContractError("parameters must have unique names")
        if isinstance(self.run_number, bool) or not isinstance(self.run_number, int):
            raise LLMEvaluationContractError("run_number must be an integer")
        if self.run_number < 1:
            raise LLMEvaluationContractError("run_number must be at least 1")
        _enum(self.status, EvaluationExecutionStatus, "status")
        output = _optional_text(self.output_text, "output_text")
        error = _optional_text(self.error_message, "error_message")
        object.__setattr__(self, "output_text", output)
        object.__setattr__(self, "error_message", error)
        if self.latency_ms is not None:
            if isinstance(self.latency_ms, bool) or not isinstance(self.latency_ms, int):
                raise LLMEvaluationContractError("latency_ms must be an integer")
            if self.latency_ms < 0:
                raise LLMEvaluationContractError("latency_ms must not be negative")
        if self.status is EvaluationExecutionStatus.COMPLETED:
            if output is None or error is not None:
                raise LLMEvaluationContractError(
                    "completed traces require output_text and must not have error_message"
                )
        elif self.status in {
            EvaluationExecutionStatus.PROVIDER_ERROR,
            EvaluationExecutionStatus.TIMEOUT,
        }:
            if error is None or output is not None:
                raise LLMEvaluationContractError(
                    "failed traces require error_message and must not have output_text"
                )
        elif self.status is EvaluationExecutionStatus.ABSTAINED:
            if output is not None or error is not None:
                raise LLMEvaluationContractError(
                    "abstained traces must not contain output_text or error_message"
                )


@dataclass(frozen=True)
class DeterministicEvaluationResult:
    result_id: str
    case_id: str
    trace_id: str
    verdict: EvaluationVerdict
    passed_check_ids: tuple[str, ...]
    failed_check_ids: tuple[str, ...]
    failure_codes: tuple[str, ...]
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("result_id", "case_id", "trace_id"):
            object.__setattr__(
                self, field_name, _required_text(getattr(self, field_name), field_name)
            )
        _enum(self.verdict, EvaluationVerdict, "verdict")
        for field_name in (
            "passed_check_ids",
            "failed_check_ids",
            "failure_codes",
            "limitations",
        ):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(getattr(self, field_name), field_name),
            )
        if set(self.passed_check_ids).intersection(self.failed_check_ids):
            raise LLMEvaluationContractError(
                "a deterministic check cannot both pass and fail"
            )
        if self.verdict is EvaluationVerdict.PASSED and (
            self.failed_check_ids or self.failure_codes
        ):
            raise LLMEvaluationContractError(
                "passed deterministic results must not contain failures"
            )
        if self.verdict is EvaluationVerdict.FAILED and not self.failed_check_ids:
            raise LLMEvaluationContractError(
                "failed deterministic results require failed_check_ids"
            )
        if self.verdict is EvaluationVerdict.NOT_EVALUATED and (
            self.passed_check_ids or self.failed_check_ids or self.failure_codes
        ):
            raise LLMEvaluationContractError(
                "not-evaluated deterministic results must not contain checks"
            )


@dataclass(frozen=True)
class ExternalMetricResult:
    metric_result_id: str
    case_id: str
    trace_id: str
    metric_name: str
    metric_version: str
    disposition: ExternalMetricDisposition
    rationale: tuple[str, ...]
    score: float | None = None
    threshold: float | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "metric_result_id",
            "case_id",
            "trace_id",
            "metric_name",
            "metric_version",
        ):
            object.__setattr__(
                self, field_name, _required_text(getattr(self, field_name), field_name)
            )
        _enum(self.disposition, ExternalMetricDisposition, "disposition")
        object.__setattr__(
            self,
            "rationale",
            _text_tuple(self.rationale, "rationale", allow_empty=False),
        )
        if self.score is not None:
            object.__setattr__(self, "score", _score(self.score, "score"))
        if self.threshold is not None:
            object.__setattr__(self, "threshold", _score(self.threshold, "threshold"))
        error = _optional_text(self.error_message, "error_message")
        object.__setattr__(self, "error_message", error)
        if self.disposition is ExternalMetricDisposition.ERROR:
            if error is None:
                raise LLMEvaluationContractError(
                    "external metric errors require error_message"
                )
        elif error is not None:
            raise LLMEvaluationContractError(
                "non-error external metric results must not have error_message"
            )
        if self.disposition in {
            ExternalMetricDisposition.SUPPORTS,
            ExternalMetricDisposition.FLAGS,
        } and self.score is None:
            raise LLMEvaluationContractError(
                "supporting or flagging external metrics require score"
            )


@dataclass(frozen=True)
class EvaluationOutput:
    output_id: str
    input_id: str
    trace: ModelExecutionTrace
    deterministic_result: DeterministicEvaluationResult
    external_metric_results: tuple[ExternalMetricResult, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "output_id", _required_text(self.output_id, "output_id"))
        object.__setattr__(self, "input_id", _required_text(self.input_id, "input_id"))
        if not isinstance(self.trace, ModelExecutionTrace):
            raise LLMEvaluationContractError("trace must be a ModelExecutionTrace")
        if not isinstance(self.deterministic_result, DeterministicEvaluationResult):
            raise LLMEvaluationContractError(
                "deterministic_result must be a DeterministicEvaluationResult"
            )
        _typed_tuple(
            self.external_metric_results,
            ExternalMetricResult,
            "external_metric_results",
        )
        if self.trace.input_id != self.input_id:
            raise LLMEvaluationContractError("trace input_id must match output input_id")
        if self.deterministic_result.trace_id != self.trace.trace_id:
            raise LLMEvaluationContractError(
                "deterministic result trace_id must match output trace"
            )
        if self.deterministic_result.case_id != self.trace.case_id:
            raise LLMEvaluationContractError(
                "deterministic result case_id must match output trace"
            )
        metric_ids = tuple(item.metric_result_id for item in self.external_metric_results)
        if len(set(metric_ids)) != len(metric_ids):
            raise LLMEvaluationContractError(
                "external_metric_results must have unique IDs"
            )
        if any(
            item.case_id != self.trace.case_id or item.trace_id != self.trace.trace_id
            for item in self.external_metric_results
        ):
            raise LLMEvaluationContractError(
                "external metric results must match the output case and trace"
            )


@dataclass(frozen=True)
class EvaluationDisagreement:
    disagreement_id: str
    case_id: str
    trace_id: str
    deterministic_result_id: str
    external_metric_result_id: str
    category: EvaluationDisagreementCategory
    rationale: tuple[str, ...]
    review_required: bool

    def __post_init__(self) -> None:
        for field_name in (
            "disagreement_id",
            "case_id",
            "trace_id",
            "deterministic_result_id",
            "external_metric_result_id",
        ):
            object.__setattr__(
                self, field_name, _required_text(getattr(self, field_name), field_name)
            )
        _enum(self.category, EvaluationDisagreementCategory, "category")
        object.__setattr__(
            self,
            "rationale",
            _text_tuple(self.rationale, "rationale", allow_empty=False),
        )
        if not isinstance(self.review_required, bool):
            raise LLMEvaluationContractError("review_required must be boolean")
        if self.category in {
            EvaluationDisagreementCategory.DETERMINISTIC_FAIL_EXTERNAL_PASS,
            EvaluationDisagreementCategory.DETERMINISTIC_PASS_EXTERNAL_FAIL,
        } and not self.review_required:
            raise LLMEvaluationContractError(
                "deterministic/external disagreements require review"
            )


@dataclass(frozen=True)
class ResponsibilityDecision:
    decision_id: str
    responsibility: LLMResponsibility
    status: ResponsibilityDecisionStatus
    rationale: tuple[str, ...]
    evidence_case_ids: tuple[str, ...]
    required_controls: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision_id", _required_text(self.decision_id, "decision_id")
        )
        _enum(self.responsibility, LLMResponsibility, "responsibility")
        _enum(self.status, ResponsibilityDecisionStatus, "status")
        object.__setattr__(
            self,
            "rationale",
            _text_tuple(self.rationale, "rationale", allow_empty=False),
        )
        object.__setattr__(
            self,
            "evidence_case_ids",
            _text_tuple(self.evidence_case_ids, "evidence_case_ids", allow_empty=False),
        )
        object.__setattr__(
            self,
            "required_controls",
            _text_tuple(self.required_controls, "required_controls"),
        )
        if (
            self.status
            is ResponsibilityDecisionStatus.APPROVED_WITH_DETERMINISTIC_VALIDATION
            and not self.required_controls
        ):
            raise LLMEvaluationContractError(
                "approval with deterministic validation requires controls"
            )


@dataclass(frozen=True)
class ControlledEvaluationReport:
    report_id: str
    dataset_version: str
    case_ids: tuple[str, ...]
    output_ids: tuple[str, ...]
    disagreement_ids: tuple[str, ...]
    responsibility_decisions: tuple[ResponsibilityDecision, ...]
    conclusion: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "report_id", _required_text(self.report_id, "report_id"))
        object.__setattr__(
            self,
            "dataset_version",
            _required_text(self.dataset_version, "dataset_version"),
        )
        for field_name in ("case_ids", "output_ids", "disagreement_ids"):
            object.__setattr__(
                self,
                field_name,
                _text_tuple(
                    getattr(self, field_name),
                    field_name,
                    allow_empty=field_name == "disagreement_ids",
                ),
            )
        _typed_tuple(
            self.responsibility_decisions,
            ResponsibilityDecision,
            "responsibility_decisions",
            allow_empty=False,
        )
        responsibilities = tuple(
            item.responsibility for item in self.responsibility_decisions
        )
        if len(set(responsibilities)) != len(responsibilities):
            raise LLMEvaluationContractError(
                "responsibility_decisions must contain one decision per responsibility"
            )
        known_case_ids = set(self.case_ids)
        if any(
            not set(item.evidence_case_ids) <= known_case_ids
            for item in self.responsibility_decisions
        ):
            raise LLMEvaluationContractError(
                "responsibility decisions may reference only report case_ids"
            )
        object.__setattr__(
            self, "conclusion", _required_text(self.conclusion, "conclusion")
        )
