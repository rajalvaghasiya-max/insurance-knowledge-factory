from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import DecisionGateOutput
from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput, build_section as explanation_section
from insurance_intelligence.contracts.response import ResponseAssemblerInput
from insurance_intelligence.response.assembler import ResponseAssemblyError, assemble_sections
from insurance_intelligence.response.registry import build_format_definition


def _decision(decision="APPROVED"):
    return DecisionGateOutput(
        contract_version="1.0", request_id="req-1", decision_id="dec-1", decision=decision,
        finding_dispositions=(), safety_issues=(), clarifications=(), blocked_content=(),
        response_packet=object() if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} else None,
        limitations=(), human_review_reasons=(), confidence=0.9, decision_trace=(),
    )


def _explanation(*sections, status="DRAFTED", limitations=(), audience="CUSTOMER"):
    return ExplanationGeneratorOutput(
        contract_version="1.0", request_id="req-1", explanation_id="exp-1", audience=audience,
        reading_level="SIMPLE", explanation_mode="PLAIN_LANGUAGE" if status != "CLARIFICATION_DRAFTED" else "CLARIFICATION_REQUEST",
        sections=tuple(sections), terminology_substitutions=(), fidelity_checks=(), fidelity_status="VERIFIED",
        limitations=tuple(limitations), explanation_status=status, confidence=0.9, explanation_trace=(),
    )


def _input(explanation, decision="APPROVED", response_format="STANDARD", context=None):
    return ResponseAssemblerInput(
        contract_version="1.0", request_id="req-1", decision_output=_decision(decision),
        explanation_output=explanation, response_format=response_format, assembly_context=dict(context or {}),
    )


def _answer_format(**overrides):
    values = dict(
        format_id="answer-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",),
        response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
        section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "IMPACT", "LIMITATION", "EVIDENCE"),
        direct_answer_policy="REQUIRED", evidence_policy="WHEN_AVAILABLE", limitation_policy="REQUIRED_WHEN_PRESENT",
        clarification_policy="FORBIDDEN", priority=10,
    )
    values.update(overrides)
    return build_format_definition(**values)


def _clarification_format(**overrides):
    values = dict(
        format_id="clar-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",),
        response_statuses=("CLARIFICATION_REQUIRED",), section_order=("CLARIFICATION",),
        allowed_section_types=("CLARIFICATION",), direct_answer_policy="FORBIDDEN", evidence_policy="FORBIDDEN",
        limitation_policy="FORBIDDEN", assumption_policy="FORBIDDEN", clarification_policy="REQUIRED", priority=10,
    )
    values.update(overrides)
    return build_format_definition(**values)


def _section(section_id="exp-sec-1", section_type="DIRECT_ANSWER", text="You bear 10% when the condition applies.", **kwargs):
    values = dict(
        section_id=section_id, section_type=section_type, status="DRAFTED", text=text,
        approved_finding_ids=("finding-1",), evidence_ids=("ev-1",), limitation_ids=(), clarification_ids=(),
    )
    values.update(kwargs)
    return explanation_section(**values)


def test_assembles_direct_answer_and_evidence_reference():
    result = assemble_sections(_input(_explanation(_section())), _answer_format())
    assert result.direct_answer == "You bear 10% when the condition applies."
    assert result.sections[0].section_type == "DIRECT_ANSWER"
    assert result.evidence_references[0].source_id == "ev-1"
    assert result.sections[0].evidence_reference_ids == (result.evidence_references[0].reference_id,)


def test_falls_back_to_first_explanatory_section_without_rewriting():
    source = _section(section_type="MEANING", text="The clause creates conditional cost sharing.")
    result = assemble_sections(_input(_explanation(source)), _answer_format())
    assert result.direct_answer == source.text


def test_sections_follow_format_order_not_input_order():
    impact = _section(section_id="impact", section_type="IMPACT", text="You pay part of the claim.")
    condition = _section(section_id="condition", section_type="CONDITION", text="This applies only in listed cities.")
    direct = _section(section_id="direct")
    result = assemble_sections(_input(_explanation(impact, condition, direct)), _answer_format())
    assert [item.section_type for item in result.sections] == ["DIRECT_ANSWER", "CONDITION", "IMPACT"]


def test_disallowed_section_type_is_excluded():
    internal = _section(section_type="INTERNAL_REVIEW_NOTE", text="Internal only")
    direct = _section()
    result = assemble_sections(_input(_explanation(internal, direct)), _answer_format())
    assert [item.section_type for item in result.sections] == ["DIRECT_ANSWER"]


def test_withheld_explanation_section_is_not_exposed():
    withheld = explanation_section(
        section_id="hidden", section_type="MEANING", status="WITHHELD", text="Hidden",
        approved_finding_ids=("finding-1",), evidence_ids=("ev-1",),
    )
    result = assemble_sections(_input(_explanation(withheld, _section())), _answer_format())
    assert all(item.text != "Hidden" for item in result.sections)


def test_evidence_is_deduplicated_and_finding_links_are_merged():
    first = _section(section_id="a", approved_finding_ids=("finding-1",))
    second = _section(section_id="b", section_type="IMPACT", approved_finding_ids=("finding-2",))
    result = assemble_sections(_input(_explanation(first, second)), _answer_format())
    assert len(result.evidence_references) == 1
    assert result.evidence_references[0].approved_finding_ids == ("finding-1", "finding-2")


def test_context_supplies_evidence_label_and_locator():
    context = {"evidence_labels": {"ev-1": "Policy wording"}, "evidence_locators": {"ev-1": "page 39"}}
    result = assemble_sections(_input(_explanation(_section()), context=context), _answer_format())
    assert result.evidence_references[0].label == "Policy wording"
    assert result.evidence_references[0].locator == "page 39"


def test_limitations_and_assumptions_are_preserved():
    limited = _section(section_type="LIMITATION", limitation_ids=("lim-1",), text="Only when the trigger applies.")
    result = assemble_sections(
        _input(_explanation(_section(), limited, limitations=("Only when the trigger applies.",)), context={"assumptions": ("Illustrative context",)}),
        _answer_format(),
    )
    assert result.limitations == ("Only when the trigger applies.",)
    assert result.assumptions == ("Illustrative context",)


def test_required_limitation_text_fails_closed_when_only_id_exists():
    limited = _section(section_type="LIMITATION", limitation_ids=("lim-1",), text="Conditional.")
    with pytest.raises(ResponseAssemblyError, match="limitation text"):
        assemble_sections(_input(_explanation(_section(), limited)), _answer_format())


def test_clarification_path_contains_only_question_and_no_evidence():
    clarification = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="In which city was treatment taken?", clarification_ids=("clar-1",),
    )
    result = assemble_sections(
        _input(_explanation(clarification, status="CLARIFICATION_DRAFTED"), decision="CLARIFICATION_REQUIRED"),
        _clarification_format(),
    )
    assert result.direct_answer is None
    assert result.clarification_questions == ("In which city was treatment taken?",)
    assert result.evidence_references == ()
    assert [item.section_type for item in result.sections] == ["CLARIFICATION"]


def test_answer_path_rejects_clarification_content():
    clarification = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="Which city?", clarification_ids=("clar-1",),
    )
    with pytest.raises(ResponseAssemblyError, match="clarification"):
        assemble_sections(_input(_explanation(_section(), clarification)), _answer_format(allowed_section_types=("DIRECT_ANSWER", "CLARIFICATION"), section_order=("DIRECT_ANSWER", "CLARIFICATION")))


def test_format_mismatch_is_rejected():
    with pytest.raises(ResponseAssemblyError, match="response_format"):
        assemble_sections(_input(_explanation(_section()), response_format="COMPACT"), _answer_format())


def test_audience_mismatch_is_rejected():
    with pytest.raises(ResponseAssemblyError, match="audience"):
        assemble_sections(_input(_explanation(_section(), audience="ADVISOR")), _answer_format())


def test_response_status_mismatch_is_rejected():
    with pytest.raises(ResponseAssemblyError, match="mapped response status"):
        assemble_sections(_input(_explanation(_section())), _answer_format(response_statuses=("ANSWER_WITH_LIMITATIONS",)))


def test_section_word_limit_is_enforced():
    long_text = "word " * 20
    with pytest.raises(ResponseAssemblyError, match="max_section_words"):
        assemble_sections(_input(_explanation(_section(text=long_text))), _answer_format(max_section_words=5))


def test_direct_answer_word_limit_is_enforced():
    text = "one two three four five six"
    with pytest.raises(ResponseAssemblyError, match="max_direct_answer_words"):
        assemble_sections(_input(_explanation(_section(text=text))), _answer_format(max_direct_answer_words=5))


def test_max_sections_is_enforced():
    sections = (_section(section_id="a"), _section(section_id="b", section_type="IMPACT"))
    with pytest.raises(ResponseAssemblyError, match="max_sections"):
        assemble_sections(_input(_explanation(*sections)), _answer_format(max_sections=1))


def test_required_evidence_policy_fails_when_no_evidence_exists():
    plain = explanation_section(section_id="plain", section_type="DIRECT_ANSWER", status="DRAFTED", text="Approved text")
    with pytest.raises(ResponseAssemblyError, match="requires evidence"):
        assemble_sections(_input(_explanation(plain)), _answer_format(evidence_policy="REQUIRED"))


def test_required_direct_answer_fails_without_eligible_content():
    limitation = explanation_section(section_id="lim", section_type="LIMITATION", status="DRAFTED", text="A limitation")
    with pytest.raises(ResponseAssemblyError, match="direct answer"):
        assemble_sections(_input(_explanation(limitation, limitations=("A limitation",))), _answer_format())


def test_outputs_are_deterministic_for_identical_inputs():
    input_value = _input(_explanation(_section()))
    definition = _answer_format()
    assert assemble_sections(input_value, definition) == assemble_sections(input_value, definition)


def test_draft_is_frozen():
    result = assemble_sections(_input(_explanation(_section())), _answer_format())
    with pytest.raises(FrozenInstanceError):
        result.direct_answer = "changed"  # type: ignore[misc]
