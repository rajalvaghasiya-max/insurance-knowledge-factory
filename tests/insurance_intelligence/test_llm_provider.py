import pytest

from insurance_intelligence.contracts.llm_rendering import (
    build_candidate_section,
    build_provider_request,
    build_rendering_packet,
)
from insurance_intelligence.llm.provider import (
    DeterministicFakeProvider,
    LLMProviderError,
    ProviderInvocationResult,
    invoke_provider,
)


def request(provider_name="deterministic_fake"):
    packet = build_rendering_packet(
        packet_id="packet-1", request_id="request-1", decision_id="decision-1",
        explanation_id="explanation-1", audience="CUSTOMER", reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING", source_section_ids=("source-1",),
        approved_finding_ids=("finding-1",), approved_evidence_ids=("evidence-1",),
    )
    return build_provider_request(
        provider_request_id="provider-request-1", request_id="request-1", rendering_id="rendering-1",
        provider_name=provider_name, model_name="model-1", packet=packet,
    )


def section():
    return build_candidate_section(
        section_id="candidate-1", source_section_id="source-1", section_type="MEANING",
        text="You pay 10% when the condition applies.", approved_finding_ids=("finding-1",),
        evidence_ids=("evidence-1",),
    )


def test_fake_provider_is_protocol_compatible():
    provider = DeterministicFakeProvider(sections=(section(),))
    assert provider.provider_name == "deterministic_fake"


def test_successful_invocation_returns_contract_response():
    result = invoke_provider(DeterministicFakeProvider(sections=(section(),)), request())
    assert isinstance(result, ProviderInvocationResult)
    assert result.response.status == "SUCCEEDED"
    assert result.normalized_failure is None


def test_successful_invocation_is_attempted_once():
    provider = DeterministicFakeProvider(sections=(section(),))
    invoke_provider(provider, request())
    assert provider.call_count == 1


def test_invocation_identity_is_deterministic():
    provider = DeterministicFakeProvider(sections=(section(),))
    assert invoke_provider(provider, request()).invocation_id == invoke_provider(provider, request()).invocation_id


def test_token_usage_is_deterministic():
    result = invoke_provider(DeterministicFakeProvider(sections=(section(),)), request())
    assert result.response.token_usage.total_tokens == 17


def test_timeout_is_normalized():
    result = invoke_provider(DeterministicFakeProvider(failure="TIMEOUT"), request())
    assert result.response.status == "TIMEOUT"
    assert result.normalized_failure == "TIMEOUT"


def test_provider_error_is_normalized():
    result = invoke_provider(DeterministicFakeProvider(failure="ERROR"), request())
    assert result.response.status == "FAILED"
    assert result.normalized_failure == "PROVIDER_ERROR"


def test_invalid_response_is_normalized():
    result = invoke_provider(DeterministicFakeProvider(failure="INVALID_RESPONSE"), request())
    assert result.response.status == "FAILED"
    assert result.response.provider_metadata["exception_type"] == "TypeError"


def test_provider_identity_must_match_request():
    with pytest.raises(LLMProviderError, match="identity"):
        invoke_provider(DeterministicFakeProvider(provider_name="other", sections=(section(),)), request())


def test_request_type_is_enforced():
    with pytest.raises(TypeError, match="ProviderRenderRequest"):
        invoke_provider(DeterministicFakeProvider(sections=(section(),)), object())


def test_fake_provider_requires_sections_on_success():
    result = invoke_provider(DeterministicFakeProvider(), request())
    assert result.response.status == "FAILED"


def test_fake_provider_rejects_unknown_failure_mode():
    with pytest.raises(ValueError, match="failure mode"):
        DeterministicFakeProvider(failure="RETRY")
