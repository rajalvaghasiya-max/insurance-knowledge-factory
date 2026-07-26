"""Controlled provider execution harness for MO-022F.4."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic_ns
from typing import Callable, Iterable

from insurance_intelligence.contracts.llm_evaluation import (
    EvaluationCase,
    EvaluationExecutionStatus,
    EvaluationInput,
    EvaluationOutput,
    ModelExecutionTrace,
    ModelParameter,
)
from insurance_intelligence.evaluation.deterministic import DeterministicLLMEvaluator
from insurance_intelligence.evaluation.provider import (
    ControlledEvaluationProvider,
    ControlledProviderError,
    ControlledProviderExecutionError,
    ControlledProviderTimeout,
    ProviderRequest,
    ProviderResponse,
)


class ControlledHarnessError(ValueError):
    """Raised when harness configuration or provider behaviour is invalid."""


@dataclass(frozen=True)
class ControlledHarnessConfig:
    provider: str
    model: str
    model_version: str
    prompt_version: str
    parameters: tuple[ModelParameter, ...]
    timeout_seconds: float

    def __post_init__(self) -> None:
        for name in ("provider", "model", "model_version", "prompt_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ControlledHarnessError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.parameters, tuple) or not all(
            isinstance(item, ModelParameter) for item in self.parameters
        ):
            raise ControlledHarnessError(
                "parameters must be a tuple of ModelParameter values"
            )
        names = tuple(item.name for item in self.parameters)
        if len(names) != len(set(names)):
            raise ControlledHarnessError("parameters must have unique names")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise ControlledHarnessError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0:
            raise ControlledHarnessError("timeout_seconds must be greater than zero")


Clock = Callable[[], int]


def _stable_id(prefix: str, case_id: str, run_number: int) -> str:
    return f"{prefix}-{case_id}-run-{run_number}"


def build_evaluation_input(
    case: EvaluationCase,
    *,
    prompt_version: str,
    run_number: int,
) -> EvaluationInput:
    return EvaluationInput(
        input_id=_stable_id("input", case.case_id, run_number),
        case_id=case.case_id,
        prompt_version=prompt_version,
        governed_evidence_ids=case.governed_evidence_ids,
        approved_finding_ids=case.approved_finding_ids,
        audience=case.audience,
    )


def execute_controlled_case(
    case: EvaluationCase,
    *,
    provider: ControlledEvaluationProvider,
    config: ControlledHarnessConfig,
    run_number: int,
    clock: Clock = monotonic_ns,
) -> EvaluationOutput:
    if isinstance(run_number, bool) or not isinstance(run_number, int) or run_number < 1:
        raise ControlledHarnessError("run_number must be an integer of at least 1")
    if not isinstance(provider, ControlledEvaluationProvider):
        raise ControlledHarnessError("provider must implement ControlledEvaluationProvider")

    evaluation_input = build_evaluation_input(
        case, prompt_version=config.prompt_version, run_number=run_number
    )
    request = ProviderRequest(
        evaluation_input=evaluation_input,
        case=case,
        provider=config.provider,
        model=config.model,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        parameters=config.parameters,
        timeout_seconds=config.timeout_seconds,
        run_number=run_number,
    )

    started = clock()
    status: EvaluationExecutionStatus
    output_text: str | None = None
    error_message: str | None = None
    try:
        response = provider.execute(request)
        if not isinstance(response, ProviderResponse):
            raise ControlledProviderExecutionError(
                "provider returned a value that is not ProviderResponse"
            )
        if response.abstained:
            status = EvaluationExecutionStatus.ABSTAINED
        else:
            status = EvaluationExecutionStatus.COMPLETED
            output_text = response.output_text
    except ControlledProviderTimeout as exc:
        status = EvaluationExecutionStatus.TIMEOUT
        error_message = str(exc).strip() or exc.__class__.__name__
    except ControlledProviderError as exc:
        status = EvaluationExecutionStatus.PROVIDER_ERROR
        error_message = str(exc).strip() or exc.__class__.__name__
    except Exception as exc:  # fail closed while retaining an auditable trace
        status = EvaluationExecutionStatus.PROVIDER_ERROR
        error_message = f"unexpected provider error: {exc.__class__.__name__}: {exc}"
    finished = clock()
    latency_ms = max(0, (finished - started) // 1_000_000)

    trace = ModelExecutionTrace(
        trace_id=_stable_id("trace", case.case_id, run_number),
        input_id=evaluation_input.input_id,
        case_id=case.case_id,
        provider=config.provider,
        model=config.model,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        parameters=config.parameters,
        run_number=run_number,
        status=status,
        output_text=output_text,
        error_message=error_message,
        latency_ms=latency_ms,
    )
    deterministic_result = DeterministicLLMEvaluator().evaluate(case, trace)
    return EvaluationOutput(
        output_id=_stable_id("output", case.case_id, run_number),
        input_id=evaluation_input.input_id,
        trace=trace,
        deterministic_result=deterministic_result,
    )


def execute_controlled_cases(
    cases: Iterable[EvaluationCase],
    *,
    provider: ControlledEvaluationProvider,
    config: ControlledHarnessConfig,
    run_number: int,
    clock: Clock = monotonic_ns,
) -> tuple[EvaluationOutput, ...]:
    ordered = tuple(sorted(cases, key=lambda item: item.case_id))
    case_ids = tuple(case.case_id for case in ordered)
    if len(case_ids) != len(set(case_ids)):
        raise ControlledHarnessError("cases must have unique case_id values")
    return tuple(
        execute_controlled_case(
            case,
            provider=provider,
            config=config,
            run_number=run_number,
            clock=clock,
        )
        for case in ordered
    )
