from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_clarification_requirement,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    build_fidelity_check as build_explanation_check,
    build_output as build_explanation_output,
    build_section as build_explanation_section,
)
from insurance_intelligence.contracts.llm_rendering import (
    LLMRenderingContractError,
    build_candidate_section,
    build_fallback_record,
    build_fidelity_check,
    build_input,
    build_output,
    build_provider_request,
    build_provider_response,
    build_rendering_packet,
    build_token_usage,
    build_trace_event,
)


def approved_decision():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="Supported with explicit condition.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        confidence=0.9,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Condition remains material.",),
        confidence=0.9,
    )


def deterministic_explanation():
    section = build_explanation_section(
        section_id="source-section-1",
        section_type="MEANING",
        status="DRAFTED",
        text="When the condition applies, the insured pays 10% of the admissible claim amount.",
        approved_finding_ids=("finding-1",),
        evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
    )
    check = build_explanation_check(
        check_id="source-check-1",
        check_type="CONDITION_PRESERVATION",
        status="PASSED",
        description="Condition is explicit.",
        source_references=("finding-1",),
        section_ids=("source-section-1",),
    )
    return build_explanation_output(
        request_id="request-1",
        explanation_id="explanation-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        sections=(section,),
        fidelity_checks=(check,),
        fidelity_status="VERIFIED",
        limitations=("Condition remains material.",),
        explanation_status="DRAFTED_WITH_LIMITATIONS",
        confidence=0.9,
    )


def clarification_decision():
    clarification = build_clarification_requirement(
        clarification_id="clarification-1",
        topic="conditional_copayment",
        question_key="trigger_status",
        reason="Trigger context is missing.",
        priority="HIGH",
        required_context_keys=("trigger_status",),
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-2",
        decision="CLARIFICATION_REQUIRED",
        clarifications=(clarification,),
        confidence=0.4,
    )


def clarification_explanation():
    section = build_explanation_section(
        section_id="source-section-c",
        section_type="CLARIFICATION",
        status="DRAFTED",
        text="Please confirm whether the documented trigger applies.",
        clarification_ids=("clarification-1",),
    )
    return build_explanation_output(
        request_id="request-1",
        explanation_id="explanation-c",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLARIFICATION_REQUEST",
        sections=(section,),
        fidelity_status="VERIFIED",
        explanation_status="CLARIFICATION_DRAFTED",
        confidence=0.4,
    )


def packet():
    return build_rendering_packet(
        packet_id="render-packet-1",
        request_id="request-1",
        decision_id="decision-1",
        explanation_id="explanation-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        source_section_ids=("source-section-1",),
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        prohibited_operations=("RECOMMEND",),
    )


def candidate():
    return build_candidate_section(
        section_id="candidate-1",
        source_section_id="source-section-1",
        section_type="MEANING",
        text="When this condition applies, you pay 10% of the admissible claim amount.",
        approved_finding_ids=("finding-1",),
        evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
    )


def provider_response():
    return build_provider_response(
        provider_response_id="provider-response-1",
        provider_request_id="provider-request-1",
        status="SUCCEEDED",
        candidate_sections=(candidate(),),
        token_usage=build_token_usage(input_tokens=100, output_tokens=30, total_tokens=130),
        finish_reason="stop",
    )


def passed_check():
    return build_fidelity_check(
        check_id="check-1",
        check_type="NUMERIC_FIDELITY",
        status="PASSED",
        description="The documented 10% remains unchanged.",
        source_section_ids=("source-section-1",),
        candidate_section_ids=("candidate-1",),
    )


def test_input_accepts_verified_deterministic_explanation():
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        deterministic_explanation=deterministic_explanation(),
        provider_name="fake-provider",
        model_name="fake-model",
    )
    assert item.provider_name == "fake-provider"


def test_input_rejects_request_mismatch():
    with pytest.raises(LLMRenderingContractError, match="request_id must match"):
        build_input(
            request_id="other",
            decision_output=approved_decision(),
            deterministic_explanation=deterministic_explanation(),
            provider_name="p",
            model_name="m",
        )


def test_input_rejects_unverified_deterministic_explanation():
    bad = build_explanation_output(
        request_id="request-1",
        explanation_id="bad",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
        fidelity_checks=(
            build_explanation_check(
                check_id="bad-check",
                check_type="NO_NEW_FACTS",
                status="FAILED",
                description="Failed.",
            ),
        ),
        fidelity_status="FAILED",
        explanation_status="WITHHELD",
    )
    with pytest.raises(LLMRenderingContractError, match="not eligible"):
        build_input(
            request_id="request-1",
            decision_output=approved_decision(),
            deterministic_explanation=bad,
            provider_name="p",
            model_name="m",
        )


def test_clarification_input_requires_clarification_draft():
    with pytest.raises(LLMRenderingContractError, match="clarification-only"):
        build_input(
            request_id="request-1",
            decision_output=clarification_decision(),
            deterministic_explanation=deterministic_explanation(),
            provider_name="p",
            model_name="m",
        )


def test_clarification_input_is_accepted():
    item = build_input(
        request_id="request-1",
        decision_output=clarification_decision(),
        deterministic_explanation=clarification_explanation(),
        provider_name="p",
        model_name="m",
    )
    assert item.deterministic_explanation.explanation_status == "CLARIFICATION_DRAFTED"


def test_packet_requires_source_section():
    with pytest.raises(LLMRenderingContractError, match="source section"):
        build_rendering_packet(
            packet_id="p",
            request_id="r",
            decision_id="d",
            explanation_id="e",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="PLAIN_LANGUAGE",
            source_section_ids=(),
            clarification_ids=("c",),
        )


def test_finding_packet_requires_evidence():
    with pytest.raises(LLMRenderingContractError, match="evidence"):
        build_rendering_packet(
            packet_id="p",
            request_id="r",
            decision_id="d",
            explanation_id="e",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="PLAIN_LANGUAGE",
            source_section_ids=("s",),
            approved_finding_ids=("f",),
        )


def test_packet_rejects_mixed_finding_and_clarification_scope():
    with pytest.raises(LLMRenderingContractError, match="cannot mix"):
        build_rendering_packet(
            packet_id="p",
            request_id="r",
            decision_id="d",
            explanation_id="e",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="PLAIN_LANGUAGE",
            source_section_ids=("s",),
            approved_finding_ids=("f",),
            approved_evidence_ids=("ev",),
            clarification_ids=("c",),
        )


def test_provider_request_forbids_tools_browsing_and_memory():
    for field in ("tools_enabled", "browsing_enabled", "memory_enabled"):
        kwargs = {field: True}
        with pytest.raises(LLMRenderingContractError, match="forbids"):
            build_provider_request(
                provider_request_id="pr",
                request_id="request-1",
                rendering_id="render-1",
                provider_name="p",
                model_name="m",
                packet=packet(),
                **kwargs,
            )


def test_provider_request_requires_low_temperature():
    with pytest.raises(LLMRenderingContractError, match="temperature"):
        build_provider_request(
            provider_request_id="pr",
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            packet=packet(),
            temperature=0.9,
        )


def test_candidate_finding_section_requires_evidence():
    with pytest.raises(LLMRenderingContractError, match="evidence"):
        build_candidate_section(
            section_id="c",
            source_section_id="s",
            section_type="MEANING",
            text="Text",
            approved_finding_ids=("f",),
        )


def test_token_usage_must_add_up():
    with pytest.raises(LLMRenderingContractError, match="must equal"):
        build_token_usage(input_tokens=10, output_tokens=5, total_tokens=20)


def test_successful_provider_response_requires_candidate_sections():
    with pytest.raises(LLMRenderingContractError, match="requires candidate"):
        build_provider_response(
            provider_response_id="resp",
            provider_request_id="req",
            status="SUCCEEDED",
        )


def test_failed_provider_response_requires_error_message():
    with pytest.raises(LLMRenderingContractError, match="error_message"):
        build_provider_response(
            provider_response_id="resp",
            provider_request_id="req",
            status="FAILED",
        )


def test_failed_provider_response_cannot_expose_candidate_sections():
    with pytest.raises(LLMRenderingContractError, match="cannot expose"):
        build_provider_response(
            provider_response_id="resp",
            provider_request_id="req",
            status="FAILED",
            candidate_sections=(candidate(),),
            error_message="failed",
        )


def test_candidate_is_immutable():
    item = candidate()
    with pytest.raises(FrozenInstanceError):
        item.text = "changed"  # type: ignore[misc]


def test_trace_sequence_must_be_positive():
    with pytest.raises(LLMRenderingContractError, match="positive integer"):
        build_trace_event(
            trace_id="trace",
            sequence=0,
            event_type="RENDERING_STARTED",
            decision="START",
            basis="Input received.",
            order_marker="0000",
        )


def test_rendered_output_requires_successful_provider_response():
    with pytest.raises(LLMRenderingContractError, match="successful provider"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            rendered_sections=(candidate(),),
            fidelity_checks=(passed_check(),),
            fidelity_status="VERIFIED",
            rendering_status="RENDERED",
            confidence=0.9,
        )


def test_rendered_output_accepts_verified_candidate():
    output = build_output(
        request_id="request-1",
        rendering_id="render-1",
        provider_name="p",
        model_name="m",
        rendered_sections=(candidate(),),
        provider_response=provider_response(),
        fidelity_checks=(passed_check(),),
        fidelity_status="VERIFIED",
        rendering_status="RENDERED",
        confidence=0.9,
    )
    assert output.rendered_sections[0].evidence_ids == ("evidence-1",)


def test_rendered_with_limitations_requires_limitations():
    with pytest.raises(LLMRenderingContractError, match="requires limitations"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            rendered_sections=(candidate(),),
            provider_response=provider_response(),
            fidelity_checks=(passed_check(),),
            fidelity_status="VERIFIED_WITH_LIMITATIONS",
            rendering_status="RENDERED_WITH_LIMITATIONS",
        )


def test_fallback_used_requires_fallback_record():
    with pytest.raises(LLMRenderingContractError, match="requires fallback"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            fidelity_status="FAILED",
            rendering_status="FALLBACK_USED",
        )


def test_fallback_output_cannot_expose_rejected_sections():
    fallback = build_fallback_record(
        fallback_id="fallback-1",
        reason="FIDELITY_FAILURE",
        deterministic_explanation_id="explanation-1",
        rejected_provider_response_id="provider-response-1",
        description="Candidate changed meaning.",
    )
    with pytest.raises(LLMRenderingContractError, match="cannot expose"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            rendered_sections=(candidate(),),
            provider_response=provider_response(),
            fidelity_checks=(
                build_fidelity_check(
                    check_id="failed-check",
                    check_type="NUMERIC_FIDELITY",
                    status="FAILED",
                    description="Number changed.",
                    candidate_section_ids=("candidate-1",),
                ),
            ),
            fidelity_status="FAILED",
            fallback=fallback,
            rendering_status="FALLBACK_USED",
        )


def test_fidelity_check_cannot_reference_unknown_candidate():
    with pytest.raises(LLMRenderingContractError, match="unknown candidate"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            rendered_sections=(candidate(),),
            provider_response=provider_response(),
            fidelity_checks=(
                build_fidelity_check(
                    check_id="check-x",
                    check_type="NUMERIC_FIDELITY",
                    status="PASSED",
                    description="Checked.",
                    candidate_section_ids=("unknown",),
                ),
            ),
            fidelity_status="VERIFIED",
            rendering_status="RENDERED",
        )


def test_trace_order_must_be_unique_and_ordered():
    first = build_trace_event(
        trace_id="trace-1",
        sequence=2,
        event_type="RENDERING_STARTED",
        decision="START",
        basis="Started.",
        order_marker="0002",
    )
    second = build_trace_event(
        trace_id="trace-2",
        sequence=1,
        event_type="RENDERING_COMPLETED",
        decision="DONE",
        basis="Done.",
        order_marker="0001",
    )
    with pytest.raises(LLMRenderingContractError, match="unique and ordered"):
        build_output(
            request_id="request-1",
            rendering_id="render-1",
            provider_name="p",
            model_name="m",
            rendered_sections=(candidate(),),
            provider_response=provider_response(),
            fidelity_checks=(passed_check(),),
            fidelity_status="VERIFIED",
            rendering_status="RENDERED",
            rendering_trace=(first, second),
        )


def test_output_has_no_final_answer_or_recommendation_fields():
    output = build_output(
        request_id="request-1",
        rendering_id="render-1",
        provider_name="p",
        model_name="m",
        rendered_sections=(candidate(),),
        provider_response=provider_response(),
        fidelity_checks=(passed_check(),),
        fidelity_status="VERIFIED",
        rendering_status="RENDERED",
    )
    assert not hasattr(output, "final_answer")
    assert not hasattr(output, "recommendation")
