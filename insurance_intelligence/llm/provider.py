"""Provider-neutral controlled LLM invocation boundary (MO-022B and GSI P1A)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol, Sequence, runtime_checkable

from insurance_intelligence.contracts.llm_rendering import (
    CandidateRenderedSection,
    ProviderRenderRequest,
    ProviderRenderResponse,
    build_provider_response,
    build_token_usage,
)


class LLMProviderError(RuntimeError):
    """Raised when a provider adapter cannot complete a controlled request."""


@runtime_checkable
class LLMRendererProvider(Protocol):
    """Legacy rendering-specific provider boundary retained unchanged."""

    @property
    def provider_name(self) -> str: ...

    def render(self, request: ProviderRenderRequest) -> ProviderRenderResponse: ...


@dataclass(frozen=True)
class ProviderInvocationResult:
    invocation_id: str
    request: ProviderRenderRequest
    response: ProviderRenderResponse
    attempted: bool
    normalized_failure: str | None


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def invoke_provider(provider: LLMRendererProvider, request: ProviderRenderRequest) -> ProviderInvocationResult:
    """Invoke the legacy renderer exactly once and normalize adapter failures."""
    if not isinstance(request, ProviderRenderRequest):
        raise TypeError("request must be ProviderRenderRequest")
    if not isinstance(provider, LLMRendererProvider):
        raise TypeError("provider must implement LLMRendererProvider")
    if provider.provider_name != request.provider_name:
        raise LLMProviderError("provider identity must match request.provider_name")

    invocation_id = _stable_id("llm-inv", request.provider_request_id, request.provider_name, request.model_name)
    try:
        response = provider.render(request)
        if not isinstance(response, ProviderRenderResponse):
            raise TypeError("provider returned non-contract response")
        if response.provider_request_id != request.provider_request_id:
            raise LLMProviderError("provider response request identity mismatch")
        return ProviderInvocationResult(invocation_id, request, response, True, None)
    except TimeoutError as exc:
        response = build_provider_response(
            provider_response_id=_stable_id("llm-res", invocation_id, "timeout"),
            provider_request_id=request.provider_request_id,
            status="TIMEOUT",
            error_message=str(exc) or "provider timeout",
            provider_metadata={"normalized_by": "invoke_provider"},
        )
        return ProviderInvocationResult(invocation_id, request, response, True, "TIMEOUT")
    except Exception as exc:  # fail closed at the adapter boundary
        response = build_provider_response(
            provider_response_id=_stable_id("llm-res", invocation_id, type(exc).__name__),
            provider_request_id=request.provider_request_id,
            status="FAILED",
            error_message=str(exc) or type(exc).__name__,
            provider_metadata={"normalized_by": "invoke_provider", "exception_type": type(exc).__name__},
        )
        return ProviderInvocationResult(invocation_id, request, response, True, "PROVIDER_ERROR")


@dataclass(frozen=True)
class TextProviderRequest:
    """Use-case-neutral text request carried by the existing LLM provider runtime."""

    provider_request_id: str
    provider_name: str
    model_name: str
    system_prompt: str
    user_prompt: str
    timeout_seconds: float

    def __post_init__(self) -> None:
        for name in (
            "provider_request_id",
            "provider_name",
            "model_name",
            "system_prompt",
            "user_prompt",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty text")
            object.__setattr__(self, name, value.strip())
        if isinstance(self.timeout_seconds, bool) or not isinstance(
            self.timeout_seconds, (int, float)
        ):
            raise ValueError("timeout_seconds must be numeric")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")


@dataclass(frozen=True)
class TextProviderResponse:
    provider_request_id: str
    status: str
    output_text: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.provider_request_id, str) or not self.provider_request_id.strip():
            raise ValueError("provider_request_id must be non-empty text")
        if self.status not in {"SUCCEEDED", "TIMEOUT", "FAILED"}:
            raise ValueError("unsupported text provider status")
        if self.status == "SUCCEEDED":
            if not isinstance(self.output_text, str) or not self.output_text.strip():
                raise ValueError("SUCCEEDED response requires non-empty output_text")
            if self.error_message is not None:
                raise ValueError("SUCCEEDED response cannot carry error_message")
            object.__setattr__(self, "output_text", self.output_text.strip())
        else:
            if self.output_text is not None:
                raise ValueError("failed text provider response cannot carry output_text")
            if not isinstance(self.error_message, str) or not self.error_message.strip():
                raise ValueError("failed text provider response requires error_message")
            object.__setattr__(self, "error_message", self.error_message.strip())


@runtime_checkable
class LLMTextProvider(Protocol):
    """Shared text provider transport; it carries text but grants no domain authority."""

    @property
    def provider_name(self) -> str: ...

    def complete(self, request: TextProviderRequest) -> TextProviderResponse: ...


@dataclass(frozen=True)
class TextProviderInvocationResult:
    invocation_id: str
    request: TextProviderRequest
    response: TextProviderResponse
    attempted: bool
    normalized_failure: str | None


def invoke_text_provider(
    provider: LLMTextProvider,
    request: TextProviderRequest,
) -> TextProviderInvocationResult:
    """Invoke one shared text provider exactly once and fail closed on adapter errors."""
    if not isinstance(request, TextProviderRequest):
        raise TypeError("request must be TextProviderRequest")
    if not isinstance(provider, LLMTextProvider):
        raise TypeError("provider must implement LLMTextProvider")
    if provider.provider_name != request.provider_name:
        raise LLMProviderError("provider identity must match request.provider_name")

    invocation_id = _stable_id(
        "llm-text-inv",
        request.provider_request_id,
        request.provider_name,
        request.model_name,
    )
    try:
        response = provider.complete(request)
        if not isinstance(response, TextProviderResponse):
            raise TypeError("provider returned non-contract text response")
        if response.provider_request_id != request.provider_request_id:
            raise LLMProviderError("provider response request identity mismatch")
        normalized_failure = None if response.status == "SUCCEEDED" else response.status
        return TextProviderInvocationResult(
            invocation_id, request, response, True, normalized_failure
        )
    except TimeoutError as exc:
        response = TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="TIMEOUT",
            error_message=str(exc) or "provider timeout",
        )
        return TextProviderInvocationResult(invocation_id, request, response, True, "TIMEOUT")
    except Exception as exc:  # fail closed at the shared provider boundary
        response = TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="FAILED",
            error_message=str(exc) or type(exc).__name__,
        )
        return TextProviderInvocationResult(
            invocation_id, request, response, True, "PROVIDER_ERROR"
        )


class DeterministicFakeProvider:
    """Offline rendering provider for repeatable tests; it never performs I/O."""

    def __init__(
        self,
        *,
        provider_name: str = "deterministic_fake",
        sections: Sequence[CandidateRenderedSection] = (),
        failure: str | None = None,
    ) -> None:
        if not provider_name.strip():
            raise ValueError("provider_name must be non-empty")
        if failure not in {None, "TIMEOUT", "ERROR", "INVALID_RESPONSE"}:
            raise ValueError("unsupported fake provider failure mode")
        self._provider_name = provider_name
        self._sections = tuple(sections)
        self._failure = failure
        self.call_count = 0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def render(self, request: ProviderRenderRequest) -> ProviderRenderResponse:
        self.call_count += 1
        if self._failure == "TIMEOUT":
            raise TimeoutError("deterministic fake timeout")
        if self._failure == "ERROR":
            raise LLMProviderError("deterministic fake provider error")
        if self._failure == "INVALID_RESPONSE":
            return object()  # type: ignore[return-value]
        sections = self._sections
        if not sections:
            raise LLMProviderError("deterministic fake requires candidate sections")
        input_tokens = len(request.packet.source_section_ids) * 10
        output_tokens = sum(max(1, len(section.text.split())) for section in sections)
        return build_provider_response(
            provider_response_id=_stable_id("llm-res", request.provider_request_id, request.model_name),
            provider_request_id=request.provider_request_id,
            status="SUCCEEDED",
            candidate_sections=sections,
            token_usage=build_token_usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=input_tokens + output_tokens,
            ),
            finish_reason="stop",
            provider_metadata={"deterministic": True},
        )


class DeterministicFakeTextProvider:
    """Offline shared-text provider used to falsify transport and containment behavior."""

    def __init__(
        self,
        *,
        output_text: str | None = None,
        provider_name: str = "deterministic_text_fake",
        failure: str | None = None,
    ) -> None:
        if not provider_name.strip():
            raise ValueError("provider_name must be non-empty")
        if failure not in {None, "TIMEOUT", "ERROR", "INVALID_RESPONSE"}:
            raise ValueError("unsupported fake provider failure mode")
        self._provider_name = provider_name
        self._output_text = output_text
        self._failure = failure
        self.call_count = 0
        self.last_request: TextProviderRequest | None = None

    @property
    def provider_name(self) -> str:
        return self._provider_name

    def complete(self, request: TextProviderRequest) -> TextProviderResponse:
        self.call_count += 1
        self.last_request = request
        if self._failure == "TIMEOUT":
            raise TimeoutError("deterministic fake text timeout")
        if self._failure == "ERROR":
            raise LLMProviderError("deterministic fake text provider error")
        if self._failure == "INVALID_RESPONSE":
            return object()  # type: ignore[return-value]
        if not isinstance(self._output_text, str) or not self._output_text.strip():
            raise LLMProviderError("deterministic fake text provider requires output_text")
        return TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="SUCCEEDED",
            output_text=self._output_text,
        )
