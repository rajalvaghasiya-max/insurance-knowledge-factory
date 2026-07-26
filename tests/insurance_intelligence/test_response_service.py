from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import (
    DecisionGateOutput,
    build_approved_response_packet,
    build_clarification_requirement,
)
from insurance_intelligence.contracts.explanation import (
    ExplanationGeneratorOutput,
    build_section as explanation_section,
)
from insurance_intelligence.contracts.response import ResponseAssemblerInput
from insurance_intelligence.response.registry import (
    ResponseFormatRegistry,
    build_format_definition,
)
from insurance_intelligence.response.service import ResponseServiceError, assemble_response


def _decision(decision="APPROVED", *, limitations=(), clarifications=(), confidence=0.9):
    packet = None
    if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        packet = build_approved_response_packet(
            packet_id="packet-1",
            approved_finding_ids=("finding-1",),
            approved_evidence_ids=("ev-1",),
            limitation_ids=("lim-1",) if limitations else (),
        )
    return DecisionGateOutput(
        contract_version="1.0", request_id="req-1", decision_id="dec-1", decision=decision,
        finding_dispositions=(), safety_issues=(), clarifications=tuple(clarifications), blocked_content=(),
        response_packet=packet, limitations=tuple(limitations), human_review_reasons=(), confidence=confidence,
        decision_trace=(),
    )


def _explanation(*sections, status="DRAFTED", limitations=(), audience="CUSTOMER", confidence=0.88):
    return ExplanationGeneratorOutput(
        contract_version="1.0", request_id="req-1", explanation_id="exp-1", audience=audience,
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE" if status != "CLARIFICATION_DRAFTED" else "CLARIFICATION_REQUEST",
        sections=tuple(sections), terminology_substitutions=(), fidelity_checks=(), fidelity_status="VERIFIED",
        limitations=tuple(limitations), explanation_status=status, confidence=confidence, explanation_trace=(),
    )


def _section(section_id="direct", section_type="DIRECT_ANSWER", text="When the condition applies, you bear 10% of the eligible claim amount.", **kwargs):
    values = dict(
        section_id=section_id, section_type=section_type, status="DRAFTED", text=text,
        approved_finding_ids=("finding-1",), evidence_ids=("ev-1",), limitation_ids=(), clarification_ids=(),
    )
    values.update(kwargs)
    return explanation_section(**values)


def _input(explanation, *, decision_output=None, context=None, response_format="STANDARD"):
    return ResponseAssemblerInput(
        contract_version="1.0", request_id="req-1", decision_output=decision_output or _decision(),
        explanation_output=explanation, response_format=response_format, assembly_context=dict(context or {}),
    )


def _answer_format(**overrides):
    values = dict(
        format_id="answer-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",),
        response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
        section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        direct_answer_policy="REQUIRED", evidence_policy="WHEN_AVAILABLE",
        limitation_policy="REQUIRED_WHEN_PRESENT", clarification_policy="FORBIDDEN", priority=10,
    )
    values.update(overrides)
    return build_format_definition(**values)


def _clarification_format():
    return build_format_definition(
        format_id="clar-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",),
        response_statuses=("CLARIFICATION_REQUIRED",), section_order=("CLARIFICATION",),
        allowed_section_types=("CLARIFICATION",), direct_answer_policy="FORBIDDEN", evidence_policy="FORBIDDEN",
        limitation_policy="FORBIDDEN", assumption_policy="FORBIDDEN", clarification_policy="REQUIRED", priority=10,
    )


def _registry(*definitions):
    return ResponseFormatRegistry(definitions or (_answer_format(), _clarification_format()))


def test_star_copayment_general_meaning_produces_answer():
    output = assemble_response(_input(_explanation(_section())), _registry())
    assert output.response_status == "ANSWER"
    assert output.direct_answer == "When the condition applies, you bear 10% of the eligible claim amount."
    assert output.evidence_references[0].source_id == "ev-1"


def test_answer_preserves_condition_and_percentage():
    condition = _section(section_id="condition", section_type="CONDITION", text="This applies only when the documented city trigger applies.")
    output = assemble_response(_input(_explanation(_section(), condition)), _registry())
    text = " ".join(item.text for item in output.sections)
    assert "10%" in text
    assert "documented city trigger" in text


def test_answer_with_limitations_preserves_limitation():
    limitation = "Applicability depends on the documented condition."
    explanation = _explanation(_section(limitation_ids=("lim-1",)), limitations=(limitation,))
    output = assemble_response(
        _input(explanation, decision_output=_decision("APPROVED_WITH_LIMITATIONS", limitations=(limitation,))),
        _registry(),
    )
    assert output.response_status == "ANSWER_WITH_LIMITATIONS"
    assert output.limitations == (limitation,)


def test_case_specific_missing_trigger_produces_clarification_only():
    clarification = build_clarification_requirement(
        clarification_id="clar-1", topic="copay", question_key="treatment_city",
        reason="Trigger context is missing.", priority="HIGH", required_context_keys=("treatment_city",),
    )
    section = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="In which city will the treatment take place?", clarification_ids=("clar-1",),
    )
    output = assemble_response(
        _input(_explanation(section, status="CLARIFICATION_DRAFTED"), decision_output=_decision("CLARIFICATION_REQUIRED", clarifications=(clarification,))),
        _registry(),
    )
    assert output.response_status == "CLARIFICATION_REQUIRED"
    assert output.direct_answer is None
    assert output.evidence_references == ()
    assert output.clarification_questions == ("In which city will the treatment take place?",)


def test_response_id_is_deterministic():
    value = _input(_explanation(_section()))
    first = assemble_response(value, _registry())
    second = assemble_response(value, _registry())
    assert first.response_id == second.response_id


def test_trace_is_deterministic_and_ordered():
    output = assemble_response(_input(_explanation(_section())), _registry())
    assert [item.sequence for item in output.response_trace] == list(range(1, len(output.response_trace) + 1))
    assert output.response_trace == assemble_response(_input(_explanation(_section())), _registry()).response_trace


def test_trace_contains_start_validation_and_completion():
    output = assemble_response(_input(_explanation(_section())), _registry())
    events = [item.event_type for item in output.response_trace]
    assert events[0] == "RESPONSE_ASSEMBLY_STARTED"
    assert "RESPONSE_VALIDATED" in events
    assert events[-1] == "RESPONSE_ASSEMBLY_COMPLETED"


def test_evidence_labels_and_locators_are_preserved():
    context = {"evidence_labels": {"ev-1": "Policy wording"}, "evidence_locators": {"ev-1": "page 39"}}
    output = assemble_response(_input(_explanation(_section()), context=context), _registry())
    assert output.evidence_references[0].label == "Policy wording"
    assert output.evidence_references[0].locator == "page 39"


def test_assumptions_are_preserved():
    output = assemble_response(
        _input(_explanation(_section()), context={"assumptions": ("Treatment occurs in the stated city.",)}),
        _registry(),
    )
    assert output.assumptions == ("Treatment occurs in the stated city.",)


def test_confidence_is_capped_by_weakest_stage():
    output = assemble_response(
        _input(_explanation(_section(), confidence=0.7), decision_output=_decision(confidence=0.8)),
        _registry(),
    )
    assert output.confidence <= 0.7


def test_clarification_confidence_is_capped():
    clarification = build_clarification_requirement(
        clarification_id="clar-1", topic="copay", question_key="treatment_city",
        reason="Missing.", priority="HIGH", required_context_keys=("treatment_city",),
    )
    section = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED", text="Which city?",
        clarification_ids=("clar-1",),
    )
    output = assemble_response(
        _input(_explanation(section, status="CLARIFICATION_DRAFTED"), decision_output=_decision("CLARIFICATION_REQUIRED", clarifications=(clarification,))),
        _registry(),
    )
    assert output.confidence <= 0.75


def test_missing_eligible_format_fails_closed():
    with pytest.raises(Exception, match="no eligible response format"):
        assemble_response(_input(_explanation(_section())), ResponseFormatRegistry((_clarification_format(),)))


def test_ambiguous_format_fails_closed():
    first = _answer_format(format_id="a", priority=10)
    second = _answer_format(format_id="b", priority=10)
    with pytest.raises(Exception, match="ambiguous"):
        assemble_response(_input(_explanation(_section())), _registry(first, second))


def test_invalid_registry_type_is_rejected():
    with pytest.raises(ResponseServiceError, match="registry"):
        assemble_response(_input(_explanation(_section())), object())  # type: ignore[arg-type]


def test_invalid_input_type_is_rejected():
    with pytest.raises(ResponseServiceError, match="assembler_input"):
        assemble_response(object(), _registry())  # type: ignore[arg-type]


def test_unapproved_decision_is_rejected():
    input_value = ResponseAssemblerInput(
        contract_version="1.0", request_id="req-1", decision_output=_decision("BLOCKED"),
        explanation_output=_explanation(_section()), response_format="STANDARD", assembly_context={},
    )
    with pytest.raises(ResponseServiceError, match="unsupported decision"):
        assemble_response(input_value, _registry())


def test_response_output_is_immutable():
    output = assemble_response(_input(_explanation(_section())), _registry())
    with pytest.raises(FrozenInstanceError):
        output.response_status = "BLOCKED"  # type: ignore[misc]


def test_sections_remain_immutable():
    output = assemble_response(_input(_explanation(_section())), _registry())
    with pytest.raises(FrozenInstanceError):
        output.sections[0].text = "Changed"  # type: ignore[misc]


def test_no_recommendation_or_example_fields_exist():
    output = assemble_response(_input(_explanation(_section())), _registry())
    assert not hasattr(output, "recommendation")
    assert not hasattr(output, "generated_example")


def test_input_order_does_not_change_output_order():
    direct = _section(section_id="direct")
    condition = _section(section_id="condition", section_type="CONDITION", text="Only when the trigger applies.")
    first = assemble_response(_input(_explanation(condition, direct)), _registry())
    second = assemble_response(_input(_explanation(direct, condition)), _registry())
    assert first.sections == second.sections
