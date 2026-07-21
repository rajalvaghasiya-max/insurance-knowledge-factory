from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import (
    DecisionGateOutput,
    build_approved_response_packet,
    build_clarification_requirement,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import (
    ExplanationContractError,
    build_fidelity_check,
    build_input,
    build_output,
    build_section,
    build_terminology_substitution,
    build_trace_event,
)


def approved_decision() -> DecisionGateOutput:
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
        basis="Supported and approved with an explicit limitation.",
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
        limitations=("Condition must remain explicit.",),
        confidence=0.9,
    )


def clarification_decision() -> DecisionGateOutput:
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


def drafted_section():
    return build_section(
        section_id="section-1",
        section_type="MEANING",
        status="DRAFTED",
        text="When the condition applies, the insured pays 10% of the admissible claim amount.",
        approved_finding_ids=("finding-1",),
        evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
    )


def passed_check():
    return build_fidelity_check(
        check_id="check-1",
        check_type="CONDITION_PRESERVATION",
        status="PASSED",
        description="The triggering condition remains explicit.",
        source_references=("finding-1",),
        section_ids=("section-1",),
    )


def test_input_accepts_approved_packet():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    assert item.audience == "CUSTOMER"
    assert item.explanation_mode == "PLAIN_LANGUAGE"


def test_input_rejects_request_mismatch():
    with pytest.raises(ExplanationContractError, match="must match"):
        build_input(request_id="other", decision_output=approved_decision())


def test_input_rejects_unsupported_contract_version():
    with pytest.raises(ExplanationContractError, match="contract_version"):
        build_input(request_id="request-1", decision_output=approved_decision(), contract_version="2.0")


def test_input_rejects_invalid_audience():
    with pytest.raises(ExplanationContractError, match="audience"):
        build_input(request_id="request-1", decision_output=approved_decision(), audience="PUBLIC")


def test_input_rejects_invalid_reading_level():
    with pytest.raises(ExplanationContractError, match="reading_level"):
        build_input(request_id="request-1", decision_output=approved_decision(), reading_level="CHILD")


def test_approved_decision_rejects_clarification_mode():
    with pytest.raises(ExplanationContractError, match="cannot use clarification"):
        build_input(
            request_id="request-1",
            decision_output=approved_decision(),
            explanation_mode="CLARIFICATION_REQUEST",
        )


def test_clarification_decision_requires_clarification_mode():
    with pytest.raises(ExplanationContractError, match="require clarification"):
        build_input(request_id="request-1", decision_output=clarification_decision())


def test_clarification_decision_is_accepted_in_clarification_mode():
    item = build_input(
        request_id="request-1",
        decision_output=clarification_decision(),
        explanation_mode="CLARIFICATION_REQUEST",
    )
    assert item.explanation_mode == "CLARIFICATION_REQUEST"


def test_non_eligible_decision_is_rejected():
    decision = build_decision_output(
        request_id="request-1",
        decision_id="decision-3",
        decision="INSUFFICIENT_EVIDENCE",
    )
    with pytest.raises(ExplanationContractError, match="not eligible"):
        build_input(request_id="request-1", decision_output=decision)


def test_drafted_finding_section_requires_evidence():
    with pytest.raises(ExplanationContractError, match="preserve evidence"):
        build_section(
            section_id="section-1",
            section_type="MEANING",
            status="DRAFTED",
            text="Meaning",
            approved_finding_ids=("finding-1",),
        )


def test_clarification_section_requires_clarification_reference():
    with pytest.raises(ExplanationContractError, match="clarification IDs"):
        build_section(
            section_id="section-1",
            section_type="CLARIFICATION",
            status="DRAFTED",
            text="Please confirm the trigger status.",
        )


def test_terminology_substitution_is_immutable():
    item = build_terminology_substitution(
        substitution_id="term-1",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        approved_finding_ids=("finding-1",),
    )
    with pytest.raises(FrozenInstanceError):
        item.rendered_term = "changed"  # type: ignore[misc]


def test_trace_sequence_must_be_positive():
    with pytest.raises(ExplanationContractError, match="positive integer"):
        build_trace_event(
            trace_id="trace-1",
            sequence=0,
            event_type="EXPLANATION_STARTED",
            decision="START",
            basis="Input received.",
            order_marker="0000",
        )


def test_output_accepts_verified_draft():
    output = build_output(
        request_id="request-1",
        explanation_id="explanation-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        sections=(drafted_section(),),
        fidelity_checks=(passed_check(),),
        fidelity_status="VERIFIED",
        explanation_status="DRAFTED",
        confidence=0.9,
    )
    assert output.sections[0].evidence_ids == ("evidence-1",)


def test_output_rejects_duplicate_section_ids():
    section = drafted_section()
    with pytest.raises(ExplanationContractError, match="section IDs"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(section, section),
            fidelity_status="VERIFIED",
            explanation_status="DRAFTED",
        )


def test_output_rejects_unknown_section_in_fidelity_check():
    check = build_fidelity_check(
        check_id="check-1",
        check_type="NO_NEW_FACTS",
        status="PASSED",
        description="No facts were added.",
        section_ids=("missing",),
    )
    with pytest.raises(ExplanationContractError, match="unknown section"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            fidelity_checks=(check,),
            fidelity_status="VERIFIED",
            explanation_status="DRAFTED",
        )


def test_verified_fidelity_rejects_failed_check():
    failed = build_fidelity_check(
        check_id="check-1",
        check_type="NO_NEW_FACTS",
        status="FAILED",
        description="An unsupported fact was added.",
        section_ids=("section-1",),
    )
    with pytest.raises(ExplanationContractError, match="verified fidelity"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            fidelity_checks=(failed,),
            fidelity_status="VERIFIED",
            explanation_status="DRAFTED",
        )


def test_failed_fidelity_requires_failed_check():
    with pytest.raises(ExplanationContractError, match="requires at least one failed"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            fidelity_status="FAILED",
            explanation_status="WITHHELD",
        )


def test_drafted_with_limitations_requires_limitations():
    with pytest.raises(ExplanationContractError, match="requires limitations"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            fidelity_status="VERIFIED_WITH_LIMITATIONS",
            explanation_status="DRAFTED_WITH_LIMITATIONS",
        )


def test_clarification_draft_requires_clarification_section():
    with pytest.raises(ExplanationContractError, match="clarification section"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLARIFICATION_REQUEST",
            sections=(drafted_section(),),
            fidelity_status="VERIFIED",
            explanation_status="CLARIFICATION_DRAFTED",
        )


def test_meaning_changing_terminology_cannot_be_verified():
    term = build_terminology_substitution(
        substitution_id="term-1",
        source_term="conditional",
        rendered_term="always",
        action="SIMPLIFY",
        meaning_preserved=False,
    )
    with pytest.raises(ExplanationContractError, match="meaning-changing"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            terminology_substitutions=(term,),
            fidelity_status="VERIFIED",
            explanation_status="DRAFTED",
        )


def test_trace_must_be_ordered_and_unique():
    first = build_trace_event(
        trace_id="trace-1",
        sequence=2,
        event_type="EXPLANATION_COMPLETED",
        decision="DONE",
        basis="Completed.",
        order_marker="0002",
    )
    second = build_trace_event(
        trace_id="trace-2",
        sequence=1,
        event_type="EXPLANATION_STARTED",
        decision="START",
        basis="Started.",
        order_marker="0001",
    )
    with pytest.raises(ExplanationContractError, match="unique and ordered"):
        build_output(
            request_id="request-1",
            explanation_id="explanation-1",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode="CLAUSE_MEANING",
            sections=(drafted_section(),),
            fidelity_checks=(passed_check(),),
            fidelity_status="VERIFIED",
            explanation_status="DRAFTED",
            explanation_trace=(first, second),
        )


def test_output_has_no_final_answer_or_recommendation_fields():
    output = build_output(
        request_id="request-1",
        explanation_id="explanation-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="CLAUSE_MEANING",
        sections=(drafted_section(),),
        fidelity_checks=(passed_check(),),
        fidelity_status="VERIFIED",
        explanation_status="DRAFTED",
    )
    assert not hasattr(output, "final_answer")
    assert not hasattr(output, "recommendation")
