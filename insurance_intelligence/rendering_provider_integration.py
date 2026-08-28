"""Bridge the existing controlled renderer into Rendering Exit Safety v1.

This module deliberately reuses the existing MO-022 provider invocation/runtime
rather than creating a parallel provider stack.  The legacy renderer remains an
untrusted candidate producer; Rendering Exit Safety is the release authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from insurance_intelligence.contracts.llm_rendering import LLMRenderingInput
from insurance_intelligence.contracts.rendering_exit import (
    RenderCandidate,
    RenderConformanceResult,
    RenderEnvelope,
    build_candidate,
    build_candidate_unit,
)
from insurance_intelligence.contracts.response import ResponseAssemblerOutput
from insurance_intelligence.llm.policy import RendererModelPolicy
from insurance_intelligence.llm.provider import LLMRendererProvider
from insurance_intelligence.llm.service import HybridRenderingResult, render_with_fallback
from insurance_intelligence.rendering_exit_safety import evaluate_render_candidate


class RenderingProviderIntegrationError(ValueError):
    """Raised when the legacy renderer cannot be safely bridged to the exit gate."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class RenderingProviderIntegrationResult:
    integration_id: str
    request_id: str
    response_id: str
    legacy_result: HybridRenderingResult
    candidate: RenderCandidate | None
    conformance: RenderConformanceResult | None
    selected_response: ResponseAssemblerOutput
    rendered_text: str | None
    used_fallback: bool
    fallback_reason: str | None


def _response_to_explanation_map(envelope: RenderEnvelope) -> dict[str, str]:
    included = {
        section.section_id: section
        for section in envelope.fallback_response.sections
        if section.status == "INCLUDED"
    }
    mapping: dict[str, str] = {}
    for unit in envelope.units:
        section = included.get(unit.source_section_id)
        if section is None:
            raise RenderingProviderIntegrationError(
                "render unit source section is absent from fallback response"
            )
        if len(section.explanation_section_ids) != 1:
            raise RenderingProviderIntegrationError(
                "v1 bridge requires one explanation section per response section"
            )
        explanation_id = section.explanation_section_ids[0]
        if explanation_id in mapping:
            raise RenderingProviderIntegrationError(
                "v1 bridge requires one response section per explanation section"
            )
        mapping[explanation_id] = unit.render_unit_id
    return mapping


def _candidate_from_legacy(
    *, envelope: RenderEnvelope, legacy: HybridRenderingResult
) -> RenderCandidate:
    if legacy.fidelity_validation is None:
        raise RenderingProviderIntegrationError(
            "legacy candidate is unavailable after renderer fallback"
        )

    explanation_to_unit = _response_to_explanation_map(envelope)
    expected_by_id = {unit.render_unit_id: unit for unit in envelope.units}
    candidate_units = []

    for position, section in enumerate(legacy.fidelity_validation.accepted_sections, start=1):
        render_unit_id = explanation_to_unit.get(section.source_section_id)
        if render_unit_id is None:
            # Preserve the unsafe extra instead of normalizing it away.  The
            # exit gate will classify this as UNAUTHORIZED_RENDER_UNIT.
            render_unit_id = _stable_id(
                "unauthorized-render-unit", envelope.response_id, section.section_id
            )
            sequence = position
        else:
            sequence = expected_by_id[render_unit_id].sequence
        candidate_units.append(
            build_candidate_unit(
                render_unit_id=render_unit_id,
                rendered_text=section.text,
                sequence=sequence,
            )
        )

    return build_candidate(
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        units=tuple(candidate_units),
    )


def render_with_exit_safety(
    *,
    envelope: RenderEnvelope,
    rendering_input: LLMRenderingInput,
    policy: RendererModelPolicy,
    provider: LLMRendererProvider,
    raw_output: str | Mapping[str, object] | None = None,
) -> RenderingProviderIntegrationResult:
    """Run MO-022, then make Rendering Exit Safety the final release authority."""
    if not isinstance(envelope, RenderEnvelope):
        raise RenderingProviderIntegrationError("envelope must be RenderEnvelope")
    if not isinstance(rendering_input, LLMRenderingInput):
        raise RenderingProviderIntegrationError(
            "rendering_input must be LLMRenderingInput"
        )
    if rendering_input.request_id != envelope.request_id:
        raise RenderingProviderIntegrationError(
            "rendering_input request_id must match render envelope"
        )

    legacy = render_with_fallback(
        rendering_input,
        policy,
        provider,
        raw_output=raw_output,
    )

    if legacy.used_fallback:
        return RenderingProviderIntegrationResult(
            integration_id=_stable_id(
                "render-integration", envelope.response_id, legacy.output.rendering_status
            ),
            request_id=envelope.request_id,
            response_id=envelope.response_id,
            legacy_result=legacy,
            candidate=None,
            conformance=None,
            selected_response=envelope.fallback_response,
            rendered_text=None,
            used_fallback=True,
            fallback_reason=f"LEGACY_{legacy.output.rendering_status}",
        )

    candidate = _candidate_from_legacy(envelope=envelope, legacy=legacy)
    conformance = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    if conformance.outcome != "PASS":
        return RenderingProviderIntegrationResult(
            integration_id=_stable_id(
                "render-integration", envelope.response_id, *conformance.violations
            ),
            request_id=envelope.request_id,
            response_id=envelope.response_id,
            legacy_result=legacy,
            candidate=candidate,
            conformance=conformance,
            selected_response=envelope.fallback_response,
            rendered_text=None,
            used_fallback=True,
            fallback_reason="EXIT_CONFORMANCE_FAILED",
        )

    return RenderingProviderIntegrationResult(
        integration_id=_stable_id(
            "render-integration", envelope.response_id, "PASS"
        ),
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        legacy_result=legacy,
        candidate=candidate,
        conformance=conformance,
        selected_response=envelope.fallback_response,
        rendered_text=conformance.rendered_text,
        used_fallback=False,
        fallback_reason=None,
    )
