"""Provider-neutral controlled LLM invocation boundary (MO-022B)."""
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
    """Minimal replaceable provider boundary used by the renderer."""

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
    """Invoke exactly once and normalize adapter failures into contract responses."""
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


class DeterministicFakeProvider:
    """Offline provider for repeatable tests; it never performs I/O."""

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
