from pathlib import Path

import pytest
import requests

from insurance_intelligence.contracts.llm_evaluation import ModelParameter
from insurance_intelligence.evaluation.dataset import load_evaluation_dataset
from insurance_intelligence.evaluation.harness import ControlledHarnessConfig, execute_controlled_case
from insurance_intelligence.evaluation.openai_provider import (
    OpenAIProviderConfigurationError,
    OpenAIResponsesProvider,
    build_controlled_prompt,
)
from insurance_intelligence.evaluation.provider import ProviderRequest


FIXTURES = Path("tests/fixtures/insurance_intelligence/llm_evaluation")


class FakeResponse:
    def __init__(self, *, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _case():
    return next(case for case in load_evaluation_dataset(FIXTURES).cases if case.case_id == "kg-001")


def _request():
    case = _case()
    config = ControlledHarnessConfig(
        provider="openai",
        model="gpt-5-mini-2025-08-07",
        model_version="gpt-5-mini-2025-08-07",
        prompt_version="mo-022f-controlled-rendering-v1",
        parameters=(
            ModelParameter(name="reasoning_effort", value="low"),
            ModelParameter(name="max_output_tokens", value="500"),
        ),
        timeout_seconds=30,
    )
    from insurance_intelligence.evaluation.harness import build_evaluation_input
    return ProviderRequest(
        evaluation_input=build_evaluation_input(case, prompt_version=config.prompt_version, run_number=1),
        case=case,
        provider=config.provider,
        model=config.model,
        model_version=config.model_version,
        prompt_version=config.prompt_version,
        parameters=config.parameters,
        timeout_seconds=config.timeout_seconds,
        run_number=1,
    )


def test_prompt_is_deterministic_and_preserves_governed_identifiers():
    request = _request()
    first = build_controlled_prompt(request)
    assert first == build_controlled_prompt(request)
    assert "kg-001" in first
    assert "ev-star-copay-reviewed-statement" in first
    assert "finding-star-copay" in first
    assert "10% co-payment" in first
    assert "Do not add facts" in first


def test_provider_posts_pinned_request_and_extracts_output(monkeypatch):
    captured = {}

    def fake_post(url, *, headers, json, timeout):
        captured.update(url=url, headers=headers, body=json, timeout=timeout)
        return FakeResponse(payload={"output": [{"type": "message", "content": [{"type": "output_text", "text": "Controlled explanation."}]}]})

    monkeypatch.setattr(requests, "post", fake_post)
    response = OpenAIResponsesProvider(api_key="secret").execute(_request())
    assert response.output_text == "Controlled explanation."
    assert captured["body"]["store"] is False
    assert captured["body"]["model"] == "gpt-5-mini-2025-08-07"
    assert captured["body"]["reasoning"] == {"effort": "low"}
    assert captured["body"]["max_output_tokens"] == 500
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_harness_preserves_completed_trace_and_deterministic_result(monkeypatch):
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(payload={"output": [{"type": "message", "content": [{"type": "output_text", "text": _case().reference_output}]}]}),
    )
    config = ControlledHarnessConfig(
        provider="openai",
        model="gpt-5-mini-2025-08-07",
        model_version="gpt-5-mini-2025-08-07",
        prompt_version="mo-022f-controlled-rendering-v1",
        parameters=(),
        timeout_seconds=30,
    )
    output = execute_controlled_case(
        _case(), provider=OpenAIResponsesProvider(api_key="secret"), config=config, run_number=1
    )
    assert output.trace.status.value == "COMPLETED"
    assert output.trace.provider == "openai"
    assert output.deterministic_result.verdict.value == "PASSED"


def test_timeout_is_captured_as_auditable_trace(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout("late")

    monkeypatch.setattr(requests, "post", timeout)
    config = ControlledHarnessConfig(
        provider="openai", model="m", model_version="m", prompt_version="p", parameters=(), timeout_seconds=1
    )
    output = execute_controlled_case(
        _case(), provider=OpenAIResponsesProvider(api_key="secret"), config=config, run_number=1
    )
    assert output.trace.status.value == "TIMEOUT"
    assert output.deterministic_result.verdict.value == "NOT_EVALUATED"


def test_http_error_is_captured_as_provider_error(monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse(status_code=429, text="rate limited"))
    config = ControlledHarnessConfig(
        provider="openai", model="m", model_version="m", prompt_version="p", parameters=(), timeout_seconds=1
    )
    output = execute_controlled_case(
        _case(), provider=OpenAIResponsesProvider(api_key="secret"), config=config, run_number=1
    )
    assert output.trace.status.value == "PROVIDER_ERROR"
    assert "429" in output.trace.error_message


def test_missing_api_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OpenAIProviderConfigurationError, match="api_key"):
        OpenAIResponsesProvider.from_environment()


def test_rejects_unknown_parameter_before_network(monkeypatch):
    request = _request()
    bad = ProviderRequest(
        evaluation_input=request.evaluation_input,
        case=request.case,
        provider=request.provider,
        model=request.model,
        model_version=request.model_version,
        prompt_version=request.prompt_version,
        parameters=(ModelParameter(name="unknown", value="1"),),
        timeout_seconds=request.timeout_seconds,
        run_number=request.run_number,
    )
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: pytest.fail("network must not be called"))
    with pytest.raises(OpenAIProviderConfigurationError, match="unsupported controlled parameter"):
        OpenAIResponsesProvider(api_key="secret").execute(bad)
