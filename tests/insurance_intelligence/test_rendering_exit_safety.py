from __future__ import annotations

from insurance_intelligence.contracts.rendering_exit import build_candidate, build_candidate_unit
from insurance_intelligence.contracts.response import (
    build_evidence_reference,
    build_output,
    build_section,
)
from insurance_intelligence.rendering_exit_safety import (
    evaluate_render_candidate,
    project_render_envelope,
)


def answer_response():
    ref = build_evidence_reference(
        reference_id="ref-1",
        reference_type="EVIDENCE",
        source_id="evidence-1",
        label="Approved evidence",
        approved_finding_ids=("finding-1",),
    )
    fact = build_section(
        section_id="section-fact",
        section_type="DIRECT_ANSWER",
        status="INCLUDED",
        text="Your policy has a 20% co-pay.",
        explanation_section_ids=("explanation-fact",),
        approved_finding_ids=("finding-1",),
        evidence_reference_ids=("ref-1",),
    )
    limitation = build_section(
        section_id="section-limit",
        section_type="LIMITATION",
        status="INCLUDED",
        text="This does not determine whether that co-pay is suitable for you.",
        explanation_section_ids=("explanation-limit",),
        limitation_ids=("limitation-1",),
    )
    return build_output(
        request_id="req-1",
        response_id="response-1",
        response_status="ANSWER_WITH_LIMITATIONS",
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer=fact.text,
        sections=(fact, limitation),
        evidence_references=(ref,),
        limitations=(limitation.text,),
        confidence=1.0,
    )


def clarification_response():
    section = build_section(
        section_id="section-clarify",
        section_type="CLARIFICATION",
        status="INCLUDED",
        text="I need more information before I can answer that for your situation.",
        explanation_section_ids=("explanation-clarify",),
        clarification_ids=("clarification-1",),
    )
    return build_output(
        request_id="req-2",
        response_id="response-2",
        response_status="CLARIFICATION_REQUIRED",
        audience="CUSTOMER",
        response_format="STANDARD",
        sections=(section,),
        clarification_questions=(section.text,),
        confidence=1.0,
    )


def exact_candidate(envelope):
    return build_candidate(
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        units=tuple(
            build_candidate_unit(
                render_unit_id=unit.render_unit_id,
                rendered_text=unit.source_text,
                sequence=unit.sequence,
            )
            for unit in envelope.units
        ),
    )


def test_projection_preserves_authorization_and_requires_every_unit():
    envelope = project_render_envelope(answer_response())
    assert len(envelope.units) == 2
    assert envelope.units[0].approved_finding_ids == ("finding-1",)
    assert envelope.units[1].limitation_ids == ("limitation-1",)
    assert all(unit.required for unit in envelope.units)
    assert all(unit.render_policy == "PRESERVE_EXACT" for unit in envelope.units)


def test_exact_candidate_passes_and_exposes_rendered_text():
    envelope = project_render_envelope(answer_response())
    result = evaluate_render_candidate(envelope=envelope, candidate=exact_candidate(envelope))
    assert result.outcome == "PASS"
    assert result.violations == ()
    assert "20% co-pay" in result.rendered_text


def test_unauthorized_extra_unit_fails_commission_check():
    envelope = project_render_envelope(answer_response())
    candidate = exact_candidate(envelope)
    units = (*candidate.units, build_candidate_unit(render_unit_id="invented", rendered_text="Buy this plan.", sequence=3))
    result = evaluate_render_candidate(
        envelope=envelope,
        candidate=build_candidate(request_id="req-1", response_id="response-1", units=units),
    )
    assert result.outcome == "FAIL"
    assert "UNAUTHORIZED_RENDER_UNIT" in result.violations
    assert result.rendered_text is None


def test_missing_required_limitation_fails_omission_check_even_when_fact_is_valid():
    envelope = project_render_envelope(answer_response())
    fact = envelope.units[0]
    candidate = build_candidate(
        request_id=envelope.request_id,
        response_id=envelope.response_id,
        units=(build_candidate_unit(render_unit_id=fact.render_unit_id, rendered_text=fact.source_text, sequence=1),),
    )
    result = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    assert result.outcome == "FAIL"
    assert "REQUIRED_RENDER_UNIT_OMITTED" in result.violations


def test_missing_required_clarification_fails_closed():
    envelope = project_render_envelope(clarification_response())
    candidate = build_candidate(request_id="req-2", response_id="response-2", units=())
    result = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    assert result.outcome == "FAIL"
    assert "REQUIRED_RENDER_UNIT_OMITTED" in result.violations


def test_rewritten_safety_unit_fails_preserve_exact():
    envelope = project_render_envelope(answer_response())
    units = list(exact_candidate(envelope).units)
    safety = units[1]
    units[1] = build_candidate_unit(
        render_unit_id=safety.render_unit_id,
        rendered_text="This co-pay is probably fine for you.",
        sequence=safety.sequence,
    )
    result = evaluate_render_candidate(
        envelope=envelope,
        candidate=build_candidate(request_id="req-1", response_id="response-1", units=tuple(units)),
    )
    assert result.outcome == "FAIL"
    assert "PRESERVE_EXACT_VIOLATION" in result.violations


def test_rewritten_fact_unit_also_fails_in_v1():
    envelope = project_render_envelope(answer_response())
    units = list(exact_candidate(envelope).units)
    fact = units[0]
    units[0] = build_candidate_unit(
        render_unit_id=fact.render_unit_id,
        rendered_text="Your policy has a 30% co-pay.",
        sequence=fact.sequence,
    )
    result = evaluate_render_candidate(
        envelope=envelope,
        candidate=build_candidate(request_id="req-1", response_id="response-1", units=tuple(units)),
    )
    assert result.outcome == "FAIL"
    assert "PRESERVE_EXACT_VIOLATION" in result.violations


def test_reordered_units_fail_even_when_text_is_exact():
    envelope = project_render_envelope(answer_response())
    exact = exact_candidate(envelope)
    reversed_units = tuple(reversed(exact.units))
    result = evaluate_render_candidate(
        envelope=envelope,
        candidate=build_candidate(request_id="req-1", response_id="response-1", units=reversed_units),
    )
    assert result.outcome == "FAIL"
    assert "RENDER_UNIT_ORDER_OR_SET_MISMATCH" in result.violations


def test_identity_mismatch_fails_closed():
    envelope = project_render_envelope(answer_response())
    exact = exact_candidate(envelope)
    result = evaluate_render_candidate(
        envelope=envelope,
        candidate=build_candidate(request_id="wrong", response_id="response-1", units=exact.units),
    )
    assert result.outcome == "FAIL"
    assert "REQUEST_ID_MISMATCH" in result.violations


def test_failure_always_preserves_original_assembler_fallback_and_is_deterministic():
    response = answer_response()
    envelope = project_render_envelope(response)
    candidate = build_candidate(request_id="req-1", response_id="response-1", units=())
    first = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    second = evaluate_render_candidate(envelope=envelope, candidate=candidate)
    assert first == second
    assert first.outcome == "FAIL"
    assert first.fallback_response is response
    assert first.fallback_response.response_id == "response-1"
