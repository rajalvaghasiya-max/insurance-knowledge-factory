"""Deterministic evidence-locked prompt packet builder (MO-022C)."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping

from insurance_intelligence.contracts.llm_rendering import (
    LLMRenderingInput,
    ProviderRenderRequest,
    build_provider_request,
    build_rendering_packet,
)
from insurance_intelligence.llm.policy import RendererModelPolicy, validate_provider_request


class PromptBuilderError(ValueError):
    """Raised when approved content cannot be converted into a controlled prompt."""


MANDATORY_PROHIBITIONS = (
    "ADD_FACTS",
    "ADD_REASONING",
    "ADD_RECOMMENDATION",
    "CHANGE_NUMBERS",
    "CHANGE_CONDITIONS",
    "OMIT_LIMITATIONS",
    "CHANGE_EVIDENCE_SCOPE",
    "USE_TOOLS",
    "BROWSE",
    "USE_MEMORY",
)

SYSTEM_INSTRUCTION = (
    "Rewrite only the supplied approved sections for clarity and audience fit. "
    "Preserve every fact, number, percentage, condition, limitation, clarification boundary, "
    "finding ID, and evidence ID. Do not add reasoning, recommendations, examples, or external facts. "
    "Return structured sections only."
)


@dataclass(frozen=True)
class PromptSourceSection:
    section_id: str
    section_type: str
    text: str
    approved_finding_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceLockedPromptPacket:
    prompt_packet_id: str
    rendering_packet_id: str
    request_id: str
    system_instruction: str
    audience: str
    reading_level: str
    explanation_mode: str
    source_sections: tuple[PromptSourceSection, ...]
    limitations: tuple[str, ...]
    style_controls: Mapping[str, object]
    prohibited_operations: tuple[str, ...]
    canonical_payload: str


@dataclass(frozen=True)
class BuiltPromptRequest:
    prompt_packet: EvidenceLockedPromptPacket
    provider_request: ProviderRenderRequest


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _json_safe_style(style: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    allowed = {"tone", "locale", "verbosity", "format", "person", "channel"}
    for key in sorted(style):
        if key not in allowed:
            raise PromptBuilderError(f"unsupported style control: {key}")
        value = style[key]
        if not isinstance(value, (str, int, float, bool)) or isinstance(value, (dict, list, tuple, set)):
            raise PromptBuilderError(f"style control {key} must be a scalar")
        result[key] = value
    return result


def build_prompt_packet(rendering_input: LLMRenderingInput) -> EvidenceLockedPromptPacket:
    if not isinstance(rendering_input, LLMRenderingInput):
        raise TypeError("rendering_input must be LLMRenderingInput")

    decision = rendering_input.decision_output
    explanation = rendering_input.deterministic_explanation
    drafted = tuple(section for section in explanation.sections if section.status == "DRAFTED")
    if not drafted:
        raise PromptBuilderError("verified explanation contains no drafted sections")
    if any(section.status != "DRAFTED" for section in drafted):
        raise PromptBuilderError("only drafted sections may enter the prompt")

    section_ids = tuple(section.section_id for section in drafted)
    findings = tuple(dict.fromkeys(fid for section in drafted for fid in section.approved_finding_ids))
    evidence = tuple(dict.fromkeys(eid for section in drafted for eid in section.evidence_ids))
    limitation_ids = tuple(dict.fromkeys(lid for section in drafted for lid in section.limitation_ids))
    clarifications = tuple(dict.fromkeys(cid for section in drafted for cid in section.clarification_ids))

    if decision.decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        response = decision.response_packet
        if response is None:
            raise PromptBuilderError("approved decision is missing response packet")
        if not set(findings) <= set(response.approved_finding_ids):
            raise PromptBuilderError("drafted section exposes unapproved finding")
        if not set(evidence) <= set(response.approved_evidence_ids):
            raise PromptBuilderError("drafted section exposes unapproved evidence")
        if not set(limitation_ids) <= set(response.limitation_ids):
            raise PromptBuilderError("drafted section exposes unapproved limitation")
        prohibited = tuple(dict.fromkeys((*response.prohibited_operations, *MANDATORY_PROHIBITIONS)))
    else:
        required = {item.clarification_id for item in decision.clarifications if item.status == "REQUIRED"}
        if not clarifications or not set(clarifications) <= required:
            raise PromptBuilderError("clarification section exceeds required clarification scope")
        prohibited = MANDATORY_PROHIBITIONS

    rendering_packet_id = _stable_id(
        "render-packet", rendering_input.request_id, decision.decision_id, explanation.explanation_id, section_ids
    )
    rendering_packet = build_rendering_packet(
        packet_id=rendering_packet_id,
        request_id=rendering_input.request_id,
        decision_id=decision.decision_id,
        explanation_id=explanation.explanation_id,
        audience=explanation.audience,
        reading_level=explanation.reading_level,
        explanation_mode=explanation.explanation_mode,
        source_section_ids=section_ids,
        approved_finding_ids=findings,
        approved_evidence_ids=evidence,
        limitation_ids=limitation_ids,
        clarification_ids=clarifications,
        prohibited_operations=prohibited,
    )

    source_sections = tuple(
        PromptSourceSection(
            section_id=section.section_id,
            section_type=section.section_type,
            text=section.text,
            approved_finding_ids=section.approved_finding_ids,
            evidence_ids=section.evidence_ids,
            limitation_ids=section.limitation_ids,
            clarification_ids=section.clarification_ids,
        )
        for section in drafted
    )
    style = _json_safe_style(rendering_input.style_context)
    payload = {
        "audience": explanation.audience,
        "reading_level": explanation.reading_level,
        "explanation_mode": explanation.explanation_mode,
        "source_sections": [section.__dict__ for section in source_sections],
        "limitations": list(explanation.limitations),
        "style_controls": style,
        "prohibited_operations": list(prohibited),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    prompt_packet_id = _stable_id("prompt-packet", rendering_packet.packet_id, canonical)
    return EvidenceLockedPromptPacket(
        prompt_packet_id=prompt_packet_id,
        rendering_packet_id=rendering_packet.packet_id,
        request_id=rendering_input.request_id,
        system_instruction=SYSTEM_INSTRUCTION,
        audience=explanation.audience,
        reading_level=explanation.reading_level,
        explanation_mode=explanation.explanation_mode,
        source_sections=source_sections,
        limitations=tuple(explanation.limitations),
        style_controls=MappingProxyType(style),
        prohibited_operations=prohibited,
        canonical_payload=canonical,
    )


def build_prompt_request(
    rendering_input: LLMRenderingInput,
    policy: RendererModelPolicy,
) -> BuiltPromptRequest:
    prompt_packet = build_prompt_packet(rendering_input)
    # Rebuild the contract packet from the canonical prompt content so the provider request
    # contains identities only; the adapter receives prompt text separately from this result.
    findings = tuple(dict.fromkeys(fid for s in prompt_packet.source_sections for fid in s.approved_finding_ids))
    evidence = tuple(dict.fromkeys(eid for s in prompt_packet.source_sections for eid in s.evidence_ids))
    limitation_ids = tuple(dict.fromkeys(lid for s in prompt_packet.source_sections for lid in s.limitation_ids))
    clarifications = tuple(dict.fromkeys(cid for s in prompt_packet.source_sections for cid in s.clarification_ids))
    packet = build_rendering_packet(
        packet_id=prompt_packet.rendering_packet_id,
        request_id=rendering_input.request_id,
        decision_id=rendering_input.decision_output.decision_id,
        explanation_id=rendering_input.deterministic_explanation.explanation_id,
        audience=prompt_packet.audience,
        reading_level=prompt_packet.reading_level,
        explanation_mode=prompt_packet.explanation_mode,
        source_section_ids=tuple(s.section_id for s in prompt_packet.source_sections),
        approved_finding_ids=findings,
        approved_evidence_ids=evidence,
        limitation_ids=limitation_ids,
        clarification_ids=clarifications,
        prohibited_operations=prompt_packet.prohibited_operations,
    )
    rendering_id = _stable_id("rendering", prompt_packet.prompt_packet_id, policy.policy_id)
    request = build_provider_request(
        provider_request_id=_stable_id("provider-request", rendering_id, rendering_input.provider_name, rendering_input.model_name),
        request_id=rendering_input.request_id,
        rendering_id=rendering_id,
        provider_name=rendering_input.provider_name,
        model_name=rendering_input.model_name,
        packet=packet,
        temperature=min(0.1, policy.maximum_temperature),
        max_output_tokens=policy.maximum_output_tokens,
    )
    validate_provider_request(request, policy)
    return BuiltPromptRequest(prompt_packet=prompt_packet, provider_request=request)
