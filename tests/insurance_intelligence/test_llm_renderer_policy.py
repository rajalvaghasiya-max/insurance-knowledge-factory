import pytest

from insurance_intelligence.contracts.llm_rendering import build_provider_request, build_rendering_packet
from insurance_intelligence.llm.policy import (
    RendererPolicyError,
    build_policy_registry,
    build_renderer_policy,
    validate_provider_request,
)


def policy(**overrides):
    values = dict(provider_name="provider-a", allowed_models=("model-1", "model-2"), default_model="model-1")
    values.update(overrides)
    return build_renderer_policy(**values)


def request(**overrides):
    packet = build_rendering_packet(
        packet_id="packet-1", request_id="request-1", decision_id="decision-1",
        explanation_id="explanation-1", audience="CUSTOMER", reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING", source_section_ids=("source-1",),
        approved_finding_ids=("finding-1",), approved_evidence_ids=("evidence-1",),
    )
    values = dict(provider_request_id="provider-request-1", request_id="request-1", rendering_id="rendering-1",
                  provider_name="provider-a", model_name="model-1", packet=packet, temperature=0.0,
                  max_output_tokens=1000)
    values.update(overrides)
    return build_provider_request(**values)


def test_policy_is_fail_closed():
    item = policy()
    assert item.structured_output_required is True
    assert item.tools_allowed is item.browsing_allowed is item.memory_allowed is False
    assert item.retries_allowed == 0


def test_policy_identity_is_deterministic():
    assert policy().policy_id == policy().policy_id


def test_default_model_must_be_allowed():
    with pytest.raises(RendererPolicyError, match="allow-listed"):
        policy(default_model="model-x")


def test_models_must_be_unique():
    with pytest.raises(RendererPolicyError, match="unique"):
        policy(allowed_models=("model-1", "model-1"))


def test_temperature_is_bounded():
    with pytest.raises(RendererPolicyError, match="0.0 and 0.3"):
        policy(maximum_temperature=0.4)


def test_token_limit_must_be_positive():
    with pytest.raises(RendererPolicyError, match="positive"):
        policy(maximum_output_tokens=0)


def test_valid_request_passes_policy():
    validate_provider_request(request(), policy())


def test_provider_must_be_allowed():
    with pytest.raises(RendererPolicyError, match="provider"):
        validate_provider_request(request(provider_name="provider-b"), policy())


def test_model_must_be_allowed():
    with pytest.raises(RendererPolicyError, match="model"):
        validate_provider_request(request(model_name="model-x"), policy())


def test_request_temperature_cannot_exceed_policy():
    with pytest.raises(RendererPolicyError, match="temperature"):
        validate_provider_request(request(temperature=0.2), policy(maximum_temperature=0.1))


def test_request_tokens_cannot_exceed_policy():
    with pytest.raises(RendererPolicyError, match="token"):
        validate_provider_request(request(max_output_tokens=1200), policy(maximum_output_tokens=1000))


def test_policy_registry_is_provider_keyed_and_rejects_duplicates():
    registry = build_policy_registry((policy(), build_renderer_policy(provider_name="provider-b", allowed_models=("m",), default_model="m")))
    assert tuple(registry) == ("provider-a", "provider-b")
    with pytest.raises(RendererPolicyError, match="unique"):
        build_policy_registry((policy(), policy()))
