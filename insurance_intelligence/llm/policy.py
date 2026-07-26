"""Governed policy for controlled LLM rendering (MO-022B)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping, Sequence

from insurance_intelligence.contracts.llm_rendering import ProviderRenderRequest


class RendererPolicyError(ValueError):
    """Raised when controlled rendering configuration violates governance."""


@dataclass(frozen=True)
class RendererModelPolicy:
    policy_id: str
    provider_name: str
    allowed_models: tuple[str, ...]
    default_model: str
    maximum_temperature: float
    maximum_output_tokens: int
    structured_output_required: bool
    tools_allowed: bool
    browsing_allowed: bool
    memory_allowed: bool
    retries_allowed: int


def _stable_policy_id(provider: str, models: Sequence[str], temperature: float, tokens: int) -> str:
    payload = "\x1f".join((provider, *models, str(temperature), str(tokens)))
    return f"llm-policy-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def build_renderer_policy(
    *,
    provider_name: str,
    allowed_models: Sequence[str],
    default_model: str,
    maximum_temperature: float = 0.1,
    maximum_output_tokens: int = 1200,
) -> RendererModelPolicy:
    provider = provider_name.strip()
    models = tuple(model.strip() for model in allowed_models)
    if not provider:
        raise RendererPolicyError("provider_name must be non-empty")
    if not models or any(not model for model in models):
        raise RendererPolicyError("allowed_models must contain non-empty values")
    if len(models) != len(set(models)):
        raise RendererPolicyError("allowed_models must be unique")
    if default_model not in models:
        raise RendererPolicyError("default_model must be allow-listed")
    if isinstance(maximum_temperature, bool) or not isinstance(maximum_temperature, (int, float)):
        raise RendererPolicyError("maximum_temperature must be numeric")
    temperature = float(maximum_temperature)
    if not 0.0 <= temperature <= 0.3:
        raise RendererPolicyError("maximum_temperature must be between 0.0 and 0.3")
    if isinstance(maximum_output_tokens, bool) or not isinstance(maximum_output_tokens, int) or maximum_output_tokens < 1:
        raise RendererPolicyError("maximum_output_tokens must be a positive integer")
    return RendererModelPolicy(
        policy_id=_stable_policy_id(provider, models, temperature, maximum_output_tokens),
        provider_name=provider,
        allowed_models=models,
        default_model=default_model,
        maximum_temperature=temperature,
        maximum_output_tokens=maximum_output_tokens,
        structured_output_required=True,
        tools_allowed=False,
        browsing_allowed=False,
        memory_allowed=False,
        retries_allowed=0,
    )


def validate_provider_request(request: ProviderRenderRequest, policy: RendererModelPolicy) -> None:
    if request.provider_name != policy.provider_name:
        raise RendererPolicyError("provider is not allowed by renderer policy")
    if request.model_name not in policy.allowed_models:
        raise RendererPolicyError("model is not allowed by renderer policy")
    if request.temperature > policy.maximum_temperature:
        raise RendererPolicyError("request temperature exceeds renderer policy")
    if request.max_output_tokens > policy.maximum_output_tokens:
        raise RendererPolicyError("request token limit exceeds renderer policy")
    if policy.structured_output_required and not request.structured_output:
        raise RendererPolicyError("structured output is required")
    if request.tools_enabled or request.browsing_enabled or request.memory_enabled:
        raise RendererPolicyError("tools, browsing, and memory are prohibited")


def build_policy_registry(policies: Sequence[RendererModelPolicy]) -> Mapping[str, RendererModelPolicy]:
    result: dict[str, RendererModelPolicy] = {}
    for policy in policies:
        if policy.provider_name in result:
            raise RendererPolicyError("provider policies must be unique")
        result[policy.provider_name] = policy
    if not result:
        raise RendererPolicyError("policy registry requires at least one policy")
    return dict(result)
