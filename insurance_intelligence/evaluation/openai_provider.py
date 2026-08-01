"""OpenAI Responses API adapter for controlled MO-022F evaluation runs."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

import requests

from insurance_intelligence.evaluation.provider import (
    ControlledProviderExecutionError,
    ControlledProviderTimeout,
    ProviderRequest,
    ProviderResponse,
)


class OpenAIProviderConfigurationError(ValueError):
    """Raised when the controlled OpenAI adapter is not safely configured."""


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OpenAIProviderConfigurationError(f"{label} must be non-empty text")
    return value.strip()


def build_controlled_prompt(request: ProviderRequest) -> str:
    case = request.case
    requirements = "\n".join(
        f"- {item.component.value}: {item.expected_text}"
        for item in sorted(case.semantic_requirements, key=lambda item: item.requirement_id)
    )
    forbidden = "\n".join(
        f"- {item.value}" for item in sorted(case.forbidden_behaviours, key=lambda item: item.value)
    ) or "- None beyond the general restrictions below"
    return (
        "You are performing a controlled insurance explanation rendering evaluation.\n"
        "Render only the governed facts below for the stated audience. Do not add facts, "
        "recommend a product, predict claim payment, alter numbers, omit conditions, or infer "
        "case-specific applicability. Preserve uncertainty and abstain when the governed facts "
        "do not support a conclusion. Return explanation text only.\n\n"
        f"Case ID: {case.case_id}\n"
        f"Audience: {case.audience}\n"
        f"Responsibility: {case.responsibility.value}\n"
        f"Approved finding IDs: {', '.join(sorted(case.approved_finding_ids))}\n"
        f"Governed evidence IDs: {', '.join(sorted(case.governed_evidence_ids))}\n\n"
        f"Required governed semantics:\n{requirements}\n\n"
        f"Forbidden behaviours:\n{forbidden}\n"
    )


def _extract_output_text(payload: object) -> str:
    if not isinstance(payload, Mapping):
        raise ControlledProviderExecutionError("OpenAI response must be a JSON object")
    output = payload.get("output")
    if not isinstance(output, list):
        raise ControlledProviderExecutionError("OpenAI response is missing output items")
    texts: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping) or part.get("type") != "output_text":
                continue
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text.strip())
    if not texts:
        raise ControlledProviderExecutionError("OpenAI response contains no output_text")
    return "\n".join(texts)


@dataclass(frozen=True)
class OpenAIResponsesProvider:
    """Minimal, auditable adapter around POST /v1/responses."""

    api_key: str
    endpoint: str = "https://api.openai.com/v1/responses"

    def __post_init__(self) -> None:
        object.__setattr__(self, "api_key", _required_text(self.api_key, "api_key"))
        endpoint = _required_text(self.endpoint, "endpoint")
        if not endpoint.startswith("https://"):
            raise OpenAIProviderConfigurationError("endpoint must use HTTPS")
        object.__setattr__(self, "endpoint", endpoint)

    @classmethod
    def from_environment(cls) -> "OpenAIResponsesProvider":
        return cls(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            endpoint=os.environ.get(
                "OPENAI_RESPONSES_ENDPOINT", "https://api.openai.com/v1/responses"
            ),
        )

    def execute(self, request: ProviderRequest) -> ProviderResponse:
        body: dict[str, object] = {
            "model": request.model,
            "input": build_controlled_prompt(request),
            "store": False,
        }
        for parameter in request.parameters:
            if parameter.name == "temperature":
                body["temperature"] = float(parameter.value)
            elif parameter.name == "max_output_tokens":
                body["max_output_tokens"] = int(parameter.value)
            elif parameter.name == "reasoning_effort":
                body["reasoning"] = {"effort": parameter.value}
            else:
                raise OpenAIProviderConfigurationError(
                    f"unsupported controlled parameter: {parameter.name}"
                )
        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=request.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ControlledProviderTimeout("OpenAI request timed out") from exc
        except requests.RequestException as exc:
            raise ControlledProviderExecutionError(f"OpenAI request failed: {exc}") from exc
        if response.status_code >= 400:
            message = response.text.strip()[:500] or f"HTTP {response.status_code}"
            raise ControlledProviderExecutionError(
                f"OpenAI returned HTTP {response.status_code}: {message}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ControlledProviderExecutionError("OpenAI returned invalid JSON") from exc
        return ProviderResponse(output_text=_extract_output_text(payload))
