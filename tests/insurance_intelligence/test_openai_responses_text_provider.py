from __future__ import annotations

import json

import requests

from insurance_intelligence.llm.openai_responses_provider import (
    OPENAI_RESPONSES_ENDPOINT,
    OpenAIResponsesTextProvider,
)
from insurance_intelligence.llm.provider import TextProviderRequest, invoke_text_provider


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append(
            {"url": url, "headers": headers, "json": json, "timeout": timeout}
        )
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def request(*, with_schema: bool = True) -> TextProviderRequest:
    schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"],
        "additionalProperties": False,
    }
    return TextProviderRequest(
        provider_request_id="provider-request-1",
        provider_name="openai_responses",
        model_name="explicit-test-model",
        system_prompt="Return JSON only.",
        user_prompt='{"question":"test"}',
        timeout_seconds=7.5,
        response_schema_name="test_schema" if with_schema else None,
        response_json_schema=json.dumps(schema) if with_schema else None,
    )


def completed_payload(text: str = '{"value":"ok"}') -> dict[str, object]:
    return {
        "id": "resp_test",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }


def test_openai_adapter_sends_store_false_and_strict_schema_without_mutating_meaning() -> None:
    session = FakeSession(FakeResponse(200, completed_payload()))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "SUCCEEDED"
    assert result.response.output_text == '{"value":"ok"}'
    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["url"] == OPENAI_RESPONSES_ENDPOINT
    assert call["timeout"] == 7.5
    body = call["json"]
    assert body["model"] == "explicit-test-model"
    assert body["instructions"] == "Return JSON only."
    assert body["input"] == '{"question":"test"}'
    assert body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["name"] == "test_schema"
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
    assert call["headers"]["Authorization"] == "Bearer test-secret"


def test_openai_adapter_does_not_add_structured_format_when_request_has_no_schema() -> None:
    session = FakeSession(FakeResponse(200, completed_payload("plain text")))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request(with_schema=False))
    assert result.response.status == "SUCCEEDED"
    assert "text" not in session.calls[0]["json"]


def test_openai_timeout_normalizes_through_shared_transport() -> None:
    session = FakeSession(error=requests.Timeout("socket timeout"))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "TIMEOUT"
    assert result.normalized_failure == "TIMEOUT"
    assert len(session.calls) == 1


def test_openai_http_failure_fails_closed_without_returning_body() -> None:
    session = FakeSession(FakeResponse(429, {"error": {"message": "sensitive detail"}}))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "FAILED"
    assert result.normalized_failure == "PROVIDER_ERROR"
    assert "429" in (result.response.error_message or "")
    assert "sensitive detail" not in (result.response.error_message or "")


def test_openai_incomplete_response_fails_closed() -> None:
    session = FakeSession(FakeResponse(200, {"status": "incomplete", "output": []}))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "FAILED"
    assert result.normalized_failure == "PROVIDER_ERROR"


def test_openai_refusal_without_output_text_fails_closed() -> None:
    payload = {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [{"type": "refusal", "refusal": "cannot comply"}],
            }
        ],
    }
    session = FakeSession(FakeResponse(200, payload))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "FAILED"
    assert result.normalized_failure == "PROVIDER_ERROR"


def test_openai_invalid_json_payload_fails_closed() -> None:
    session = FakeSession(FakeResponse(200, ValueError("bad json")))
    provider = OpenAIResponsesTextProvider(api_key="test-secret", session=session)
    result = invoke_text_provider(provider, request())
    assert result.response.status == "FAILED"
    assert result.normalized_failure == "PROVIDER_ERROR"
