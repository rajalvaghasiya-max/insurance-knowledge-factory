"""Canonical render-unit projection and deterministic bidirectional conformance."""
from __future__ import annotations

from hashlib import sha256

from insurance_intelligence.contracts.rendering_exit import (
    RenderCandidate,
    RenderConformanceResult,
    RenderEnvelope,
    build_envelope,
    build_render_unit,
)
from insurance_intelligence.contracts.response import ResponseAssemblerOutput


class RenderingExitSafetyError(ValueError):
    """Raised when the rendering exit boundary cannot be evaluated safely."""


def _stable_id(prefix: str, *parts: object) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def project_render_envelope(response: ResponseAssemblerOutput) -> RenderEnvelope:
    """Project included response sections into exact-preserve canonical render units."""
    if not isinstance(response, ResponseAssemblerOutput):
        raise RenderingExitSafetyError("response must be a ResponseAssemblerOutput")

    included = tuple(section for section in response.sections if section.status == "INCLUDED")
    if not included:
        raise RenderingExitSafetyError("response contains no included sections to render")

    units = []
    for sequence, section in enumerate(included, start=1):
        units.append(
            build_render_unit(
                render_unit_id=_stable_id("render-unit", response.response_id, section.section_id),
                source_section_id=section.section_id,
                unit_type=section.section_type,
                source_text=section.text,
                approved_finding_ids=section.approved_finding_ids,
                evidence_reference_ids=section.evidence_reference_ids,
                limitation_ids=section.limitation_ids,
                clarification_ids=section.clarification_ids,
                required=True,
                render_policy="PRESERVE_EXACT",
                sequence=sequence,
            )
        )

    return build_envelope(
        request_id=response.request_id,
        response_id=response.response_id,
        units=tuple(units),
        fallback_response=response,
    )


def evaluate_render_candidate(
    *,
    envelope: RenderEnvelope,
    candidate: RenderCandidate,
) -> RenderConformanceResult:
    """Deterministically enforce no commission and no omission for render units."""
    if not isinstance(envelope, RenderEnvelope):
        raise RenderingExitSafetyError("envelope must be a RenderEnvelope")
    if not isinstance(candidate, RenderCandidate):
        raise RenderingExitSafetyError("candidate must be a RenderCandidate")

    violations: list[str] = []
    if candidate.request_id != envelope.request_id:
        violations.append("REQUEST_ID_MISMATCH")
    if candidate.response_id != envelope.response_id:
        violations.append("RESPONSE_ID_MISMATCH")

    expected_ids = tuple(unit.render_unit_id for unit in envelope.units)
    actual_ids = tuple(unit.render_unit_id for unit in candidate.units)

    unexpected = sorted(set(actual_ids) - set(expected_ids))
    missing = sorted(set(expected_ids) - set(actual_ids))
    if unexpected:
        violations.append("UNAUTHORIZED_RENDER_UNIT")
    if missing:
        violations.append("REQUIRED_RENDER_UNIT_OMITTED")
    if actual_ids != expected_ids:
        violations.append("RENDER_UNIT_ORDER_OR_SET_MISMATCH")

    expected_by_id = {unit.render_unit_id: unit for unit in envelope.units}
    candidate_by_id = {unit.render_unit_id: unit for unit in candidate.units}

    for render_unit_id in expected_ids:
        expected = expected_by_id[render_unit_id]
        actual = candidate_by_id.get(render_unit_id)
        if actual is None:
            continue
        if actual.sequence != expected.sequence:
            violations.append("RENDER_UNIT_SEQUENCE_MISMATCH")
        if expected.render_policy == "PRESERVE_EXACT" and actual.rendered_text != expected.source_text:
            violations.append("PRESERVE_EXACT_VIOLATION")

    violations = list(dict.fromkeys(violations))
    passed = not violations
    rendered_text = (
        "\n\n".join(unit.rendered_text for unit in candidate.units)
        if passed
        else None
    )
    return RenderConformanceResult(
        contract_version=envelope.contract_version,
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        outcome="PASS" if passed else "FAIL",
        violations=tuple(violations),
        rendered_text=rendered_text,
        fallback_response=envelope.fallback_response,
    )
