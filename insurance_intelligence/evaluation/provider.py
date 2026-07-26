"""Provider boundary for controlled LLM evaluation (MO-022F.4)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from insurance_intelligence.contracts.llm_evaluation import EvaluationCase, EvaluationInput, ModelParameter


class ControlledProviderError(RuntimeError):
    """Base error raised by a controlled provider adapter."""


class ControlledProviderTimeout(ControlledProviderError):
    """Raised when a provider exceeds the explicitly configured timeout."""


class ControlledProviderExecutionError(ControlledProviderError):
    """Raised when a provider fails before returning a controlled response."""


@dataclass(frozen=True)
class ProviderRequest:
    evaluation_input: EvaluationInput
    case: EvaluationCase
    provider: str
    model: str
    model_version: str
    prompt_version: str
    parameters: tuple[ModelParameter, ...]
    timeout_seconds: float
    run_number: int

    def __post_init__(self) -> None:
        if self.evaluation_input.case_id != self.case.case_id:
            raise ValueError("evaluation_input and case must reference the same case_id")
        for name in ("provider", "model", "model_version", "prompt_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())
        if not isinstance(self.parameters, tuple) or not all(
            isinstance(item, ModelParameter) for item in self.parameters
        ):
            raise ValueError("parameters must be a tuple of ModelParameter values")
        names = tuple(item.name for item in self.parameters)
        if len(names) != len(set(names)):
            raise ValueError("parameters must have unique names")
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise ValueError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if isinstance(self.run_number, bool) or not isinstance(self.run_number, int):
            raise ValueError("run_number must be an integer")
        if self.run_number < 1:
            raise ValueError("run_number must be at least 1")


@dataclass(frozen=True)
class ProviderResponse:
    output_text: str | None = None
    abstained: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.abstained, bool):
            raise ValueError("abstained must be boolean")
        if self.abstained:
            if self.output_text is not None:
                raise ValueError("abstained responses must not contain output_text")
            return
        if not isinstance(self.output_text, str) or not self.output_text.strip():
            raise ValueError("completed responses require non-empty output_text")
        object.__setattr__(self, "output_text", self.output_text.strip())


@runtime_checkable
class ControlledEvaluationProvider(Protocol):
    """Minimal adapter boundary used only by the controlled evaluation harness."""

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        """Return one response or raise an explicit controlled-provider error."""
