"""Executable controlled LLM renderer with mandatory deterministic fallback (MO-022E)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Mapping

from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput
from insurance_intelligence.contracts.llm_rendering import (
    LLMRenderingInput,
    LLMRenderingOutput,
    RenderingFidelityCheck,
    build_fallback_record,
    build_fidelity_check,
    build_output,
    build_trace_event,
)
from insurance_intelligence.llm.fidelity import FidelityValidationResult, validate_fidelity
from insurance_intelligence.llm.output_parser import LLMOutputParseError, ParsedProviderOutput, parse_provider_output
from insurance_intelligence.llm.policy import RendererModelPolicy
from insurance_intelligence.llm.prompt_builder import BuiltPromptRequest, build_prompt_request
from insurance_intelligence.llm.provider import LLMRendererProvider, ProviderInvocationResult, invoke_provider


@dataclass(frozen=True)
class HybridRenderingResult:
    service_result_id: str
    output: LLMRenderingOutput
    deterministic_explanation: ExplanationGeneratorOutput
    prompt_request: BuiltPromptRequest
    invocation: ProviderInvocationResult
    parsed_output: ParsedProviderOutput | None
    fidelity_validation: FidelityValidationResult | None
    used_fallback: bool


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _trace(rendering_id: str, events: tuple[tuple[str, str, str, tuple[str, ...], tuple[str, ...]], ...]):
    return tuple(
        build_trace_event(
            trace_id=_stable_id("llm-trace", rendering_id, index, event_type),
            sequence=index,
            event_type=event_type,
            decision=decision,
            basis=basis,
            input_references=inputs,
            output_references=outputs,
            order_marker=f"{index:02d}:{event_type}",
        )
        for index, (event_type, decision, basis, inputs, outputs) in enumerate(events, start=1)
    )


def _fallback_check(rendering_id: str, reason: str, source_ids: tuple[str, ...]) -> RenderingFidelityCheck:
    return build_fidelity_check(
        check_id=_stable_id("fallback-check", rendering_id, reason),
        check_type="STRUCTURE_VALID" if reason == "INVALID_STRUCTURE" else "NO_NEW_FACTS",
        status="REQUIRES_REVIEW",
        description=f"Candidate was not released; deterministic fallback selected because {reason}.",
        source_section_ids=source_ids,
    )


def render_with_fallback(
    rendering_input: LLMRenderingInput,
    policy: RendererModelPolicy,
    provider: LLMRendererProvider,
    *,
    raw_output: str | Mapping[str, object] | None = None,
) -> HybridRenderingResult:
    """Run the controlled renderer once and always retain the deterministic explanation."""
    if not isinstance(rendering_input, LLMRenderingInput):
        raise TypeError("rendering_input must be LLMRenderingInput")
    if not isinstance(policy, RendererModelPolicy):
        raise TypeError("policy must be RendererPolicy")

    built = build_prompt_request(rendering_input, policy)
    request = built.provider_request
    invocation = invoke_provider(provider, request)
    response = invocation.response
    rendering_id = request.rendering_id
    base_events = (
        ("RENDERING_STARTED", "STARTED", "Controlled hybrid rendering started.", (rendering_input.request_id,), (rendering_id,)),
        ("INPUT_VALIDATED", "ACCEPTED", "Input and deterministic explanation are eligible.", (rendering_input.deterministic_explanation.explanation_id,), (built.prompt_packet.prompt_packet_id,)),
        ("PACKET_BUILT", "LOCKED", "Evidence-locked provider packet built.", (built.prompt_packet.prompt_packet_id,), (request.provider_request_id,)),
        ("PROVIDER_REQUESTED", "REQUESTED", "Provider invoked exactly once.", (request.provider_request_id,), (invocation.invocation_id,)),
        ("PROVIDER_RESPONDED", response.status, response.error_message or "Provider returned a contract response.", (invocation.invocation_id,), (response.provider_response_id,)),
    )

    if response.status != "SUCCEEDED":
        reason = "TIMEOUT" if response.status == "TIMEOUT" else "PROVIDER_ERROR"
        fallback = build_fallback_record(
            fallback_id=_stable_id("fallback", rendering_id, reason), reason=reason,
            deterministic_explanation_id=rendering_input.deterministic_explanation.explanation_id,
            rejected_provider_response_id=response.provider_response_id,
            description="Provider failed; deterministic explanation remains authoritative.",
        )
        events = base_events + (
            ("FALLBACK_SELECTED", reason, "Provider failure requires deterministic fallback.", (response.provider_response_id,), (fallback.fallback_id,)),
            ("RENDERING_COMPLETED", "FALLBACK", "Completed with deterministic fallback.", (fallback.fallback_id,), (rendering_input.deterministic_explanation.explanation_id,)),
        )
        output = build_output(
            request_id=rendering_input.request_id, rendering_id=rendering_id,
            provider_name=request.provider_name, model_name=request.model_name,
            provider_response=response, fidelity_status="FAILED", fallback=fallback,
            rendering_status="PROVIDER_FAILED", limitations=(fallback.description,), confidence=0.0,
            rendering_trace=_trace(rendering_id, events),
        )
        return HybridRenderingResult(_stable_id("hybrid-result", rendering_id, output.rendering_status), output, rendering_input.deterministic_explanation, built, invocation, None, None, True)

    provider_payload = raw_output
    if provider_payload is None:
        provider_payload = {"sections": [
            {
                "section_id": section.section_id, "source_section_id": section.source_section_id,
                "section_type": section.section_type, "text": section.text,
                "approved_finding_ids": list(section.approved_finding_ids), "evidence_ids": list(section.evidence_ids),
                "limitation_ids": list(section.limitation_ids), "clarification_ids": list(section.clarification_ids),
            }
            for section in response.candidate_sections
        ]}
    try:
        parsed = parse_provider_output(provider_payload, request)
    except LLMOutputParseError as exc:
        reason = "INVALID_STRUCTURE"
        fallback = build_fallback_record(
            fallback_id=_stable_id("fallback", rendering_id, reason), reason=reason,
            deterministic_explanation_id=rendering_input.deterministic_explanation.explanation_id,
            rejected_provider_response_id=response.provider_response_id, description=str(exc),
        )
        check = _fallback_check(rendering_id, reason, request.packet.source_section_ids)
        events = base_events + (
            ("FALLBACK_SELECTED", reason, str(exc), (response.provider_response_id,), (fallback.fallback_id,)),
            ("RENDERING_COMPLETED", "FALLBACK", "Completed with deterministic fallback.", (fallback.fallback_id,), (rendering_input.deterministic_explanation.explanation_id,)),
        )
        output = build_output(
            request_id=rendering_input.request_id, rendering_id=rendering_id,
            provider_name=request.provider_name, model_name=request.model_name,
            provider_response=response, fidelity_checks=(check,), fidelity_status="REQUIRES_REVIEW",
            fallback=fallback, rendering_status="FALLBACK_USED", limitations=(str(exc),), confidence=0.0,
            rendering_trace=_trace(rendering_id, events),
        )
        return HybridRenderingResult(_stable_id("hybrid-result", rendering_id, reason), output, rendering_input.deterministic_explanation, built, invocation, None, None, True)

    fidelity = validate_fidelity(built.prompt_packet, parsed)
    if fidelity.status != "VERIFIED":
        reason = fidelity.failure_reasons[0] if fidelity.failure_reasons else "FIDELITY_FAILURE"
        if reason not in {"UNSUPPORTED_CONTENT", "NUMERIC_CHANGE", "MISSING_CONDITION", "MISSING_LIMITATION", "EVIDENCE_MISMATCH", "DECISION_SCOPE_MISMATCH"}:
            reason = "FIDELITY_FAILURE"
        fallback = build_fallback_record(
            fallback_id=_stable_id("fallback", rendering_id, reason), reason=reason,
            deterministic_explanation_id=rendering_input.deterministic_explanation.explanation_id,
            rejected_provider_response_id=response.provider_response_id,
            description="Candidate failed deterministic fidelity validation.",
        )
        check = _fallback_check(rendering_id, reason, request.packet.source_section_ids)
        events = base_events + (
            ("CANDIDATE_PARSED", "PARSED", "Structured candidate parsed.", (response.provider_response_id,), (parsed.parse_id,)),
            ("FIDELITY_VALIDATED", "FAILED", ",".join(fidelity.failure_reasons), (parsed.parse_id,), (fidelity.validation_id,)),
            ("FALLBACK_SELECTED", reason, fallback.description, (fidelity.validation_id,), (fallback.fallback_id,)),
            ("RENDERING_COMPLETED", "FALLBACK", "Completed with deterministic fallback.", (fallback.fallback_id,), (rendering_input.deterministic_explanation.explanation_id,)),
        )
        output = build_output(
            request_id=rendering_input.request_id, rendering_id=rendering_id,
            provider_name=request.provider_name, model_name=request.model_name,
            provider_response=response, fidelity_checks=(check,), fidelity_status="REQUIRES_REVIEW",
            fallback=fallback, rendering_status="FALLBACK_USED",
            limitations=tuple(fidelity.failure_reasons), confidence=0.0,
            rendering_trace=_trace(rendering_id, events),
        )
        return HybridRenderingResult(_stable_id("hybrid-result", rendering_id, reason), output, rendering_input.deterministic_explanation, built, invocation, parsed, fidelity, True)

    status = "RENDERED_WITH_LIMITATIONS" if rendering_input.deterministic_explanation.limitations else "RENDERED"
    events = base_events + (
        ("CANDIDATE_PARSED", "PARSED", "Structured candidate parsed.", (response.provider_response_id,), (parsed.parse_id,)),
        ("FIDELITY_VALIDATED", "VERIFIED", "Candidate passed deterministic fidelity validation.", (parsed.parse_id,), (fidelity.validation_id,)),
        ("RENDERING_COMPLETED", status, "Verified LLM wording released.", (fidelity.validation_id,), tuple(s.section_id for s in fidelity.accepted_sections)),
    )
    output = build_output(
        request_id=rendering_input.request_id, rendering_id=rendering_id,
        provider_name=request.provider_name, model_name=request.model_name,
        rendered_sections=fidelity.accepted_sections, provider_response=response,
        fidelity_checks=fidelity.checks, fidelity_status="VERIFIED", rendering_status=status,
        limitations=rendering_input.deterministic_explanation.limitations,
        confidence=rendering_input.deterministic_explanation.confidence,
        rendering_trace=_trace(rendering_id, events),
    )
    return HybridRenderingResult(_stable_id("hybrid-result", rendering_id, status), output, rendering_input.deterministic_explanation, built, invocation, parsed, fidelity, False)
