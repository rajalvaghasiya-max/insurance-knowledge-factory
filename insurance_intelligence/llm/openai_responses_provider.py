"""OpenAI Responses API adapter for the shared provider-neutral text transport.

This adapter transports text only. It has no insurance or interpretation authority.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

import requests

from insurance_intelligence.llm.provider import (
    LLMProviderError,
    TextProviderRequest,
    TextProviderResponse,
)

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
OPENAI_PROVIDER_NAME = "openai_responses"


class _HTTPSession(Protocol):
    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
        timeout: float,
    ) -> Any: ...


class OpenAIResponsesTextProvider:
    """Concrete OpenAI adapter behind the existing shared text-provider protocol."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str = OPENAI_RESPONSES_ENDPOINT,
        session: _HTTPSession | None = None,
        max_output_tokens: int = 1200,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("api_key must be non-empty")
        if not isinstance(endpoint, str) or not endpoint.strip().startswith("https://"):
            raise ValueError("endpoint must be an https URL")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens < 16:
            raise ValueError("max_output_tokens must be an integer of at least 16")
        self._api_key = api_key.strip()
        self._endpoint = endpoint.strip()
        self._session = session or requests.Session()
        self._max_output_tokens = max_output_tokens

    @property
    def provider_name(self) -> str:
        return OPENAI_PROVIDER_NAME

    def complete(self, request: TextProviderRequest) -> TextProviderResponse:
        if not isinstance(request, TextProviderRequest):
            raise TypeError("request must be TextProviderRequest")
        if request.provider_name != self.provider_name:
            raise LLMProviderError("request provider_name does not match OpenAI adapter")

        body: dict[str, object] = {
            "model": request.model_name,
            "instructions": request.system_prompt,
            "input": request.user_prompt,
            "store": False,
            "max_output_tokens": self._max_output_tokens,
        }
        if request.response_json_schema is not None:
            body["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": request.response_schema_name,
                    "strict": True,
                    "schema": json.loads(request.response_json_schema),
                }
            }

        try:
            response = self._session.post(
                self._endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=float(request.timeout_seconds),
            )
        except requests.Timeout as exc:
            raise TimeoutError("OpenAI Responses request timed out") from exc
        except requests.RequestException as exc:
            raise LLMProviderError(
                f"OpenAI Responses transport error: {exc.__class__.__name__}"
            ) from exc

        status_code = getattr(response, "status_code", None)
        if not isinstance(status_code, int):
            raise LLMProviderError("OpenAI Responses HTTP adapter returned no status code")
        if not 200 <= status_code < 300:
            raise LLMProviderError(f"OpenAI Responses HTTP status {status_code}")
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise LLMProviderError("OpenAI Responses returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise LLMProviderError("OpenAI Responses payload must be an object")
        status = payload.get("status")
        if status != "completed":
            raise LLMProviderError(f"OpenAI Responses status was {status!r}, not 'completed'")

        output = payload.get("output")
        if not isinstance(output, list):
            raise LLMProviderError("OpenAI Responses completed payload has no output list")
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "output_text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
        if not texts:
            raise LLMProviderError(
                "OpenAI Responses completed without usable output_text (refusal or empty output)"
            )
        return TextProviderResponse(
            provider_request_id=request.provider_request_id,
            status="SUCCEEDED",
            output_text="\n".join(texts),
        )
