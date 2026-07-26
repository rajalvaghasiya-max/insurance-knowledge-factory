"""Contracts for deterministic end-to-end Intelligence Layer evaluation (MO-021A)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

SUPPORTED_CONTRACT_VERSION = "1.0"
EVALUATION_OUTCOMES = frozenset({"PASS", "FAIL", "BLOCKED", "INVALID"})
ASSERTION_CATEGORIES = frozenset(
    {
        "STAGE_STATUS",
        "RESPONSE_STATUS",
        "REQUIRED_BEHAVIOR",
        "PROHIBITED_BEHAVIOR",
        "TRACE_EVENT",
        "DETERMINISM",
        "EVIDENCE_FIDELITY",
        "LIMITATION_FIDELITY",
        "CLARIFICATION_FIDELITY",
        "AUDIENCE_FORMAT",
    }
)
STAGE_NAMES = frozenset(
    {
        "INTENT_ANALYZER",
        "CONTEXT_BUILDER",
        "REASONING_PLANNER",
        "EVIDENCE_RESOLVER",
        "REASONING_ENGINE",
        "DECISION_GATE",
        "EXPLANATION_GENERATOR",
        "RESPONSE_ASSEMBLER",
    }
)
SCENARIO_KINDS = frozenset(
    {
        "GENERAL_EXPLANATION",
        "CASE_APPLICABILITY",
        "FAILURE_STATE",
        "UNSUPPORTED_REQUEST",
        "AUDIENCE_RENDERING",
        "DETERMINISM",
    }
)


class EvaluationContractError(ValueError):
    """Raised when an evaluation contract is invalid."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvaluationContractError(f"{label} must be a non-empty string")
    return value.strip()


def _member(value: object, allowed: frozenset[str], label: str) -> str:
    if value not in allowed:
        raise EvaluationContractError(f"{label} must be one of {sorted(allowed)}; got {value!r}")
    return value  # type: ignore[return-value]


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise EvaluationContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class StageExpectation:
    stage: str
    expected_statuses: tuple[str, ...]
    required_trace_events: tuple[str, ...]
    prohibited_trace_events: tuple[str, ...]


def build_stage_expectation(
    *,
    stage: str,
    expected_statuses: Sequence[str],
    required_trace_events: Sequence[str] = (),
    prohibited_trace_events: Sequence[str] = (),
) -> StageExpectation:
    statuses = _unique(expected_statuses, "stage_expectation.expected_statuses")
    if not statuses:
        raise EvaluationContractError("stage expectation must contain at least one expected status")
    required = _unique(required_trace_events, "stage_expectation.required_trace_events")
    prohibited = _unique(prohibited_trace_events, "stage_expectation.prohibited_trace_events")
    if set(required) & set(prohibited):
        raise EvaluationContractError("trace events cannot be both required and prohibited")
    return StageExpectation(
        stage=_member(stage, STAGE_NAMES, "stage_expectation.stage"),
        expected_statuses=statuses,
        required_trace_events=required,
        prohibited_trace_events=prohibited,
    )


@dataclass(frozen=True)
class EvaluationAssertion:
    assertion_id: str
    category: str
    description: str
    required: bool
    target_stage: str | None
    expected_values: tuple[str, ...]


def build_assertion(
    *,
    assertion_id: str,
    category: str,
    description: str,
    required: bool = True,
    target_stage: str | None = None,
    expected_values: Sequence[str] = (),
) -> EvaluationAssertion:
    if not isinstance(required, bool):
        raise EvaluationContractError("assertion.required must be boolean")
    if target_stage is not None:
        _member(target_stage, STAGE_NAMES, "assertion.target_stage")
    values = _unique(expected_values, "assertion.expected_values")
    if category in {"STAGE_STATUS", "RESPONSE_STATUS", "TRACE_EVENT"} and not values:
        raise EvaluationContractError(f"{category} assertions require expected_values")
    return EvaluationAssertion(
        assertion_id=_text(assertion_id, "assertion.assertion_id"),
        category=_member(category, ASSERTION_CATEGORIES, "assertion.category"),
        description=_text(description, "assertion.description"),
        required=required,
        target_stage=target_stage,
        expected_values=values,
    )


@dataclass(frozen=True)
class EvaluationScenario:
    contract_version: str
    scenario_id: str
    scenario_version: str
    name: str
    description: str
    scenario_kind: str
    request_text: str
    domain: str
    topic: str
    audience: str
    input_context: Mapping[str, object]
    expected_response_statuses: tuple[str, ...]
    stage_expectations: tuple[StageExpectation, ...]
    assertions: tuple[EvaluationAssertion, ...]
    required_behaviors: tuple[str, ...]
    prohibited_behaviors: tuple[str, ...]
    tags: tuple[str, ...]
    priority: int

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.scenario_id, self.scenario_version)


def build_scenario(
    *,
    scenario_id: str,
    scenario_version: str,
    name: str,
    description: str,
    scenario_kind: str,
    request_text: str,
    domain: str,
    topic: str,
    audience: str,
    expected_response_statuses: Sequence[str],
    stage_expectations: Sequence[StageExpectation],
    assertions: Sequence[EvaluationAssertion],
    input_context: Mapping[str, object] | None = None,
    required_behaviors: Sequence[str] = (),
    prohibited_behaviors: Sequence[str] = (),
    tags: Sequence[str] = (),
    priority: int = 100,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> EvaluationScenario:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EvaluationContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    if isinstance(priority, bool) or not isinstance(priority, int) or priority < 0:
        raise EvaluationContractError("priority must be a non-negative integer")
    statuses = _unique(expected_response_statuses, "scenario.expected_response_statuses")
    if not statuses:
        raise EvaluationContractError("scenario must define expected response statuses")
    stages = tuple(stage_expectations)
    if len(stages) != len({item.stage for item in stages}):
        raise EvaluationContractError("scenario stage expectations must be unique by stage")
    assertion_values = tuple(assertions)
    if len(assertion_values) != len({item.assertion_id for item in assertion_values}):
        raise EvaluationContractError("scenario assertion IDs must be unique")
    required = _unique(required_behaviors, "scenario.required_behaviors")
    prohibited = _unique(prohibited_behaviors, "scenario.prohibited_behaviors")
    if set(required) & set(prohibited):
        raise EvaluationContractError("behaviors cannot be both required and prohibited")
    return EvaluationScenario(
        contract_version=contract_version,
        scenario_id=_text(scenario_id, "scenario.scenario_id"),
        scenario_version=_text(scenario_version, "scenario.scenario_version"),
        name=_text(name, "scenario.name"),
        description=_text(description, "scenario.description"),
        scenario_kind=_member(scenario_kind, SCENARIO_KINDS, "scenario.scenario_kind"),
        request_text=_text(request_text, "scenario.request_text"),
        domain=_text(domain, "scenario.domain"),
        topic=_text(topic, "scenario.topic"),
        audience=_text(audience, "scenario.audience"),
        input_context=dict(input_context or {}),
        expected_response_statuses=statuses,
        stage_expectations=stages,
        assertions=assertion_values,
        required_behaviors=required,
        prohibited_behaviors=prohibited,
        tags=_unique(tags, "scenario.tags"),
        priority=priority,
    )


@dataclass(frozen=True)
class AssertionResult:
    assertion_id: str
    category: str
    passed: bool
    actual_values: tuple[str, ...]
    message: str


def build_assertion_result(
    *, assertion_id: str, category: str, passed: bool, actual_values: Sequence[str] = (), message: str
) -> AssertionResult:
    if not isinstance(passed, bool):
        raise EvaluationContractError("assertion_result.passed must be boolean")
    return AssertionResult(
        assertion_id=_text(assertion_id, "assertion_result.assertion_id"),
        category=_member(category, ASSERTION_CATEGORIES, "assertion_result.category"),
        passed=passed,
        actual_values=_unique(actual_values, "assertion_result.actual_values"),
        message=_text(message, "assertion_result.message"),
    )


@dataclass(frozen=True)
class EvaluationResult:
    contract_version: str
    scenario_id: str
    run_id: str
    outcome: str
    assertion_results: tuple[AssertionResult, ...]
    failed_assertion_ids: tuple[str, ...]
    blocked_reason: str | None


def build_result(
    *,
    scenario_id: str,
    run_id: str,
    outcome: str,
    assertion_results: Sequence[AssertionResult],
    blocked_reason: str | None = None,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> EvaluationResult:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise EvaluationContractError(f"contract_version must be {SUPPORTED_CONTRACT_VERSION!r}")
    result_values = tuple(assertion_results)
    if len(result_values) != len({item.assertion_id for item in result_values}):
        raise EvaluationContractError("assertion result IDs must be unique")
    validated_outcome = _member(outcome, EVALUATION_OUTCOMES, "result.outcome")
    failed = tuple(item.assertion_id for item in result_values if not item.passed)
    if validated_outcome == "PASS" and failed:
        raise EvaluationContractError("PASS result cannot contain failed assertions")
    if validated_outcome == "FAIL" and not failed:
        raise EvaluationContractError("FAIL result must contain a failed assertion")
    if validated_outcome == "BLOCKED":
        if blocked_reason is None:
            raise EvaluationContractError("BLOCKED result requires blocked_reason")
        _text(blocked_reason, "result.blocked_reason")
    elif blocked_reason is not None:
        raise EvaluationContractError("blocked_reason is allowed only for BLOCKED results")
    return EvaluationResult(
        contract_version=contract_version,
        scenario_id=_text(scenario_id, "result.scenario_id"),
        run_id=_text(run_id, "result.run_id"),
        outcome=validated_outcome,
        assertion_results=result_values,
        failed_assertion_ids=failed,
        blocked_reason=blocked_reason,
    )
