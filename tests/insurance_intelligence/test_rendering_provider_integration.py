import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    build_fidelity_check as build_expl_check,
    build_output as build_explanation_output,
    build_section as build_explanation_section,
)
from insurance_intelligence.contracts.llm_rendering import (
    build_candidate_section,
    build_input as build_rendering_input,
)
from insurance_intelligence.contracts.response import (
    build_evidence_reference,
    build_output as build_response_output,
    build_section as build_response_section,
)
from insurance_intelligence.llm.policy import build_renderer_policy
from insurance_intelligence.llm.provider import DeterministicFakeProvider
from insurance_intelligence.rendering_exit_safety import project_render_envelope
from insurance_intelligence.rendering_provider_integration import (
    RenderingProviderIntegrationError,
    render_with_exit_safety,
)


SOURCE_TEXT = "When the condition applies, the insured pays 10%."
PARAPHRASE = "When the condition applies, you pay 10%."


def fixtures():
    packet = build_approved_response_packet(
        packet_id="p",
        approved_finding_ids=("f1",),
        approved_evidence_ids=("e1",),
        limitation_ids=("l1",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="f1",
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="supported",
        approved_evidence_ids=("e1",),
        limitation_ids=("l1",),
        confidence=.9,
    )
    decision = build_decision_output(
        request_id="r1",
        decision_id="d1",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Condition applies.",),
        confidence=.9,
    )
    explanation_section = build_explanation_section(
        section_id="s1",
        section_type="MEANING",
        status="DRAFTED",
        text=SOURCE_TEXT,
        approved_finding_ids=("f1",),
        evidence_ids=("e1",),
        limitation_ids=("l1",),
    )
    check = build_expl_check(
        check_id="c1",
        check_type="NO_NEW_FACTS",
        status="PASSED",
        description="ok",
        section_ids=("s1",),
    )
    explanation = build_explanation_output(
        request_id="r1",
        explanation_id="x1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        sections=(explanation_section,),
        fidelity_checks=(check,),
        fidelity_status="VERIFIED",
        limitations=("Condition applies.",),
        explanation_status="DRAFTED_WITH_LIMITATIONS",
        confidence=.9,
    )
    rendering_input = build_rendering_input(
        request_id="r1",
        decision_output=decision,
        deterministic_explanation=explanation,
        provider_name="fake",
        model_name="model",
    )
    response_section = build_response_section(
        section_id="rs1",
        section_type="EXPLANATION",
        status="INCLUDED",
        text=SOURCE_TEXT,
        explanation_section_ids=("s1",),
        approved_finding_ids=("f1",),
        evidence_reference_ids=("ref1",),
        limitation_ids=("l1",),
    )
    response = build_response_output(
        request_id="r1",
        response_id="resp1",
        response_status="ANSWER_WITH_LIMITATIONS",
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer=SOURCE_TEXT,
        sections=(response_section,),
        evidence_references=(
            build_evidence_reference(
                reference_id="ref1",
                reference_type="EVIDENCE",
                source_id="e1",
                label="Evidence 1",
                approved_finding_ids=("f1",),
            ),
        ),
        limitations=("Condition applies.",),
        confidence=.9,
    )
    envelope = project_render_envelope(response)
    policy = build_renderer_policy(
        provider_name="fake",
        allowed_models=("model",),
        default_model="model",
        maximum_temperature=.2,
        maximum_output_tokens=500,
    )
    return rendering_input, response, envelope, policy


def provider(text=SOURCE_TEXT, *, failure=None):
    sections = () if failure else (
        build_candidate_section(
            section_id="cs1",
            source_section_id="s1",
            section_type="MEANING",
            text=text,
            approved_finding_ids=("f1",),
            evidence_ids=("e1",),
            limitation_ids=("l1",),
        ),
    )
    return DeterministicFakeProvider(
        provider_name="fake",
        sections=sections,
        failure=failure,
    )


def run(text=SOURCE_TEXT, *, failure=None):
    rendering_input, response, envelope, policy = fixtures()
    fake = provider(text, failure=failure)
    result = render_with_exit_safety(
        envelope=envelope,
        rendering_input=rendering_input,
        policy=policy,
        provider=fake,
    )
    return result, fake, response


def test_exact_preserve_candidate_passes_exit_gate():
    result, fake, _ = run()
    assert fake.call_count == 1
    assert result.used_fallback is False
    assert result.conformance is not None
    assert result.conformance.outcome == "PASS"
    assert result.rendered_text == SOURCE_TEXT


def test_legacy_accepted_paraphrase_is_rejected_by_new_exit_gate():
    result, _, response = run(PARAPHRASE)
    assert result.legacy_result.used_fallback is False
    assert result.conformance is not None
    assert result.conformance.outcome == "FAIL"
    assert "PRESERVE_EXACT_VIOLATION" in result.conformance.violations
    assert result.used_fallback is True
    assert result.selected_response is response
    assert result.rendered_text is None


def test_timeout_uses_assembler_fallback_without_exit_candidate():
    result, fake, response = run(failure="TIMEOUT")
    assert fake.call_count == 1
    assert result.used_fallback is True
    assert result.candidate is None
    assert result.conformance is None
    assert result.selected_response is response


def test_provider_error_uses_assembler_fallback():
    result, _, response = run(failure="ERROR")
    assert result.used_fallback is True
    assert result.selected_response is response
    assert result.fallback_reason == "LEGACY_PROVIDER_FAILED"


def test_invalid_provider_response_uses_assembler_fallback():
    result, _, response = run(failure="INVALID_RESPONSE")
    assert result.used_fallback is True
    assert result.selected_response is response
    assert result.rendered_text is None


def test_request_identity_mismatch_fails_before_provider_invocation():
    rendering_input, _, envelope, policy = fixtures()
    other_response = envelope.fallback_response
    from dataclasses import replace

    mismatched = replace(envelope, request_id="different")
    fake = provider()
    with pytest.raises(RenderingProviderIntegrationError):
        render_with_exit_safety(
            envelope=mismatched,
            rendering_input=rendering_input,
            policy=policy,
            provider=fake,
        )
    assert fake.call_count == 0


def test_integration_result_identity_is_deterministic():
    first, _, _ = run()
    second, _, _ = run()
    assert first.integration_id == second.integration_id


def test_exit_failure_never_releases_legacy_rendered_text():
    result, _, _ = run(PARAPHRASE)
    assert result.legacy_result.output.rendered_sections[0].text == PARAPHRASE
    assert result.rendered_text is None
