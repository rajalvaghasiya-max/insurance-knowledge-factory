from __future__ import annotations

from dataclasses import replace

import pytest

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationExecutionStatus,
    EvaluationVerdict,
    ModelParameter,
)
from insurance_intelligence.evaluation.dataset import load_evaluation_dataset
from insurance_intelligence.evaluation.harness import (
    ControlledHarnessConfig,
    ControlledHarnessError,
    build_evaluation_input,
    execute_controlled_case,
    execute_controlled_cases,
)
from insurance_intelligence.evaluation.provider import (
    ControlledProviderExecutionError,
    ControlledProviderTimeout,
    ProviderRequest,
    ProviderResponse,
)


FIXTURES = "tests/fixtures/insurance_intelligence/llm_evaluation"


class FakeProvider:
    def __init__(self, response: ProviderResponse | Exception):
        self.response = response
        self.requests: list[ProviderRequest] = []

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class StepClock:
    def __init__(self, *values: int):
        self.values = iter(values)

    def __call__(self) -> int:
        return next(self.values)


@pytest.fixture
def dataset():
    return load_evaluation_dataset(FIXTURES)


@pytest.fixture
def config():
    return ControlledHarnessConfig(
        provider="fake-provider",
        model="fake-model",
        model_version="2026-07-25",
        prompt_version="prompt-v1",
        parameters=(
            ModelParameter(name="temperature", value="0"),
            ModelParameter(name="max_tokens", value="512"),
        ),
        timeout_seconds=30.0,
    )


def test_build_input_preserves_governed_references(dataset, config):
    case = dataset.cases[0]
    value = build_evaluation_input(case, prompt_version=config.prompt_version, run_number=2)
    assert value.input_id == f"input-{case.case_id}-run-2"
    assert value.governed_evidence_ids == case.governed_evidence_ids
    assert value.approved_finding_ids == case.approved_finding_ids


def test_completed_response_produces_trace_and_deterministic_result(dataset, config):
    case = next(item for item in dataset.cases if item.case_id == "kg-001")
    provider = FakeProvider(ProviderResponse(output_text=case.reference_output))
    result = execute_controlled_case(
        case,
        provider=provider,
        config=config,
        run_number=1,
        clock=StepClock(1_000_000_000, 1_125_000_000),
    )
    assert result.trace.status is EvaluationExecutionStatus.COMPLETED
    assert result.trace.latency_ms == 125
    assert result.trace.parameters == config.parameters
    assert result.deterministic_result.verdict in {
        EvaluationVerdict.PASSED,
        EvaluationVerdict.REQUIRES_REVIEW,
    }
    assert provider.requests[0].timeout_seconds == 30.0


def test_abstention_is_preserved_and_not_evaluated(dataset, config):
    result = execute_controlled_case(
        dataset.cases[0],
        provider=FakeProvider(ProviderResponse(abstained=True)),
        config=config,
        run_number=1,
        clock=StepClock(0, 1_000_000),
    )
    assert result.trace.status is EvaluationExecutionStatus.ABSTAINED
    assert result.trace.output_text is None
    assert result.deterministic_result.verdict is EvaluationVerdict.NOT_EVALUATED


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (ControlledProviderTimeout("deadline exceeded"), EvaluationExecutionStatus.TIMEOUT),
        (
            ControlledProviderExecutionError("provider unavailable"),
            EvaluationExecutionStatus.PROVIDER_ERROR,
        ),
    ],
)
def test_controlled_provider_failures_are_captured(dataset, config, error, status):
    result = execute_controlled_case(
        dataset.cases[0],
        provider=FakeProvider(error),
        config=config,
        run_number=3,
        clock=StepClock(0, 3_000_000),
    )
    assert result.trace.status is status
    assert result.trace.error_message
    assert result.trace.run_number == 3
    assert result.deterministic_result.verdict is EvaluationVerdict.NOT_EVALUATED


def test_unexpected_provider_error_fails_closed(dataset, config):
    result = execute_controlled_case(
        dataset.cases[0],
        provider=FakeProvider(RuntimeError("boom")),
        config=config,
        run_number=1,
        clock=StepClock(0, 1),
    )
    assert result.trace.status is EvaluationExecutionStatus.PROVIDER_ERROR
    assert result.trace.error_message == "unexpected provider error: RuntimeError: boom"


def test_non_response_return_is_provider_error(dataset, config):
    class InvalidProvider:
        def execute(self, request):
            return "not-a-response"

    result = execute_controlled_case(
        dataset.cases[0],
        provider=InvalidProvider(),
        config=config,
        run_number=1,
        clock=StepClock(0, 1),
    )
    assert result.trace.status is EvaluationExecutionStatus.PROVIDER_ERROR
    assert "not ProviderResponse" in result.trace.error_message


def test_batch_execution_is_ordered_by_case_id(dataset, config):
    selected = (dataset.cases[2], dataset.cases[0], dataset.cases[1])
    provider = FakeProvider(ProviderResponse(abstained=True))
    results = execute_controlled_cases(
        selected,
        provider=provider,
        config=config,
        run_number=1,
        clock=StepClock(*(range(6))),
    )
    assert tuple(item.trace.case_id for item in results) == tuple(
        sorted(item.case_id for item in selected)
    )


def test_batch_rejects_duplicate_case_ids(dataset, config):
    case = dataset.cases[0]
    with pytest.raises(ControlledHarnessError, match="unique case_id"):
        execute_controlled_cases(
            (case, case),
            provider=FakeProvider(ProviderResponse(abstained=True)),
            config=config,
            run_number=1,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"provider": ""},
        {"model": ""},
        {"model_version": ""},
        {"prompt_version": ""},
        {"timeout_seconds": 0},
    ],
)
def test_config_has_no_hidden_defaults(config, changes):
    with pytest.raises(ControlledHarnessError):
        replace(config, **changes)


def test_config_rejects_duplicate_parameter_names(config):
    with pytest.raises(ControlledHarnessError, match="unique names"):
        replace(
            config,
            parameters=(
                ModelParameter(name="temperature", value="0"),
                ModelParameter(name="temperature", value="1"),
            ),
        )


def test_provider_request_rejects_case_mismatch(dataset, config):
    first, second = dataset.cases[:2]
    evaluation_input = build_evaluation_input(
        first, prompt_version=config.prompt_version, run_number=1
    )
    with pytest.raises(ValueError, match="same case_id"):
        ProviderRequest(
            evaluation_input=evaluation_input,
            case=second,
            provider=config.provider,
            model=config.model,
            model_version=config.model_version,
            prompt_version=config.prompt_version,
            parameters=config.parameters,
            timeout_seconds=config.timeout_seconds,
            run_number=1,
        )


def test_provider_response_invariants():
    with pytest.raises(ValueError, match="must not contain"):
        ProviderResponse(output_text="text", abstained=True)
    with pytest.raises(ValueError, match="non-empty"):
        ProviderResponse(output_text=" ")
