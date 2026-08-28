"""Contracts for deterministic Rendering Exit Safety v1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from insurance_intelligence.contracts.response import ResponseAssemblerOutput

SUPPORTED_CONTRACT_VERSION = "1.0"
UNIT_TYPES = frozenset(
    {
        "DIRECT_ANSWER",
        "EXPLANATION",
        "CONDITION",
        "IMPACT",
        "LIMITATION",
        "EVIDENCE",
        "ASSUMPTION",
        "CLARIFICATION",
        "ADVISOR_TALKING_POINT",
        "INTERNAL_NOTE",
    }
)
RENDER_POLICIES = frozenset({"PRESERVE_EXACT"})
CONFORMANCE_OUTCOMES = frozenset({"PASS", "FAIL"})


class RenderingExitContractError(ValueError):
    """Raised when a rendering-exit artifact violates its contract."""


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RenderingExitContractError(f"{label} must be a non-empty string")
    return value


def _unique(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_text(value, f"{label}[]") for value in values)
    if len(result) != len(set(result)):
        raise RenderingExitContractError(f"{label} values must be unique")
    return result


@dataclass(frozen=True)
class CanonicalRenderUnit:
    render_unit_id: str
    source_section_id: str
    unit_type: str
    source_text: str
    approved_finding_ids: tuple[str, ...]
    evidence_reference_ids: tuple[str, ...]
    limitation_ids: tuple[str, ...]
    clarification_ids: tuple[str, ...]
    required: bool
    render_policy: str
    sequence: int


def build_render_unit(
    *,
    render_unit_id: str,
    source_section_id: str,
    unit_type: str,
    source_text: str,
    sequence: int,
    approved_finding_ids: Sequence[str] = (),
    evidence_reference_ids: Sequence[str] = (),
    limitation_ids: Sequence[str] = (),
    clarification_ids: Sequence[str] = (),
    required: bool = True,
    render_policy: str = "PRESERVE_EXACT",
) -> CanonicalRenderUnit:
    if unit_type not in UNIT_TYPES:
        raise RenderingExitContractError(f"unsupported unit_type: {unit_type}")
    if render_policy not in RENDER_POLICIES:
        raise RenderingExitContractError(f"unsupported render_policy: {render_policy}")
    if not isinstance(required, bool):
        raise RenderingExitContractError("required must be boolean")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise RenderingExitContractError("sequence must be a positive integer")
    clarifications = _unique(clarification_ids, "clarification_ids")
    if unit_type == "CLARIFICATION" and not clarifications:
        raise RenderingExitContractError("CLARIFICATION units require clarification_ids")
    return CanonicalRenderUnit(
        render_unit_id=_text(render_unit_id, "render_unit_id"),
        source_section_id=_text(source_section_id, "source_section_id"),
        unit_type=unit_type,
        source_text=_text(source_text, "source_text"),
        approved_finding_ids=_unique(approved_finding_ids, "approved_finding_ids"),
        evidence_reference_ids=_unique(evidence_reference_ids, "evidence_reference_ids"),
        limitation_ids=_unique(limitation_ids, "limitation_ids"),
        clarification_ids=clarifications,
        required=required,
        render_policy=render_policy,
        sequence=sequence,
    )


@dataclass(frozen=True)
class RenderEnvelope:
    contract_version: str
    request_id: str
    response_id: str
    units: tuple[CanonicalRenderUnit, ...]
    fallback_response: ResponseAssemblerOutput


def build_envelope(
    *,
    request_id: str,
    response_id: str,
    units: Sequence[CanonicalRenderUnit],
    fallback_response: ResponseAssemblerOutput,
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> RenderEnvelope:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise RenderingExitContractError("unsupported contract_version")
    if not isinstance(fallback_response, ResponseAssemblerOutput):
        raise RenderingExitContractError("fallback_response must be ResponseAssemblerOutput")
    request_id = _text(request_id, "request_id")
    response_id = _text(response_id, "response_id")
    if fallback_response.request_id != request_id or fallback_response.response_id != response_id:
        raise RenderingExitContractError("fallback_response identity must match envelope")
    values = tuple(units)
    if not values:
        raise RenderingExitContractError("envelope requires at least one render unit")
    ids = [item.render_unit_id for item in values]
    sequences = [item.sequence for item in values]
    if len(ids) != len(set(ids)):
        raise RenderingExitContractError("render_unit_ids must be unique")
    if sequences != list(range(1, len(values) + 1)):
        raise RenderingExitContractError("render unit sequence must be contiguous and ordered")
    return RenderEnvelope(
        contract_version=contract_version,
        request_id=request_id,
        response_id=response_id,
        units=values,
        fallback_response=fallback_response,
    )


@dataclass(frozen=True)
class RenderedUnitCandidate:
    render_unit_id: str
    rendered_text: str
    sequence: int


def build_candidate_unit(*, render_unit_id: str, rendered_text: str, sequence: int) -> RenderedUnitCandidate:
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise RenderingExitContractError("candidate sequence must be a positive integer")
    return RenderedUnitCandidate(
        render_unit_id=_text(render_unit_id, "render_unit_id"),
        rendered_text=_text(rendered_text, "rendered_text"),
        sequence=sequence,
    )


@dataclass(frozen=True)
class RenderCandidate:
    contract_version: str
    request_id: str
    response_id: str
    units: tuple[RenderedUnitCandidate, ...]


def build_candidate(
    *,
    request_id: str,
    response_id: str,
    units: Sequence[RenderedUnitCandidate],
    contract_version: str = SUPPORTED_CONTRACT_VERSION,
) -> RenderCandidate:
    if contract_version != SUPPORTED_CONTRACT_VERSION:
        raise RenderingExitContractError("unsupported contract_version")
    values = tuple(units)
    ids = [item.render_unit_id for item in values]
    if len(ids) != len(set(ids)):
        raise RenderingExitContractError("candidate render_unit_ids must be unique")
    return RenderCandidate(
        contract_version=contract_version,
        request_id=_text(request_id, "request_id"),
        response_id=_text(response_id, "response_id"),
        units=values,
    )


@dataclass(frozen=True)
class RenderConformanceResult:
    contract_version: str
    request_id: str
    response_id: str
    outcome: str
    violations: tuple[str, ...]
    rendered_text: str | None
    fallback_response: ResponseAssemblerOutput
