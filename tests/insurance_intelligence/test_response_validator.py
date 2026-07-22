from dataclasses import FrozenInstanceError, replace

import pytest

from insurance_intelligence.contracts.decision import (
    DecisionGateOutput,
    build_approved_response_packet,
    build_clarification_requirement,
)
from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput, build_section as explanation_section
from insurance_intelligence.contracts.response import ResponseAssemblerInput, build_evidence_reference, build_section
from insurance_intelligence.response.assembler import ResponseAssemblyDraft, assemble_sections
from insurance_intelligence.response.registry import build_format_definition
from insurance_intelligence.response.validator import (
    ResponseIntegrityError,
    validate_response_draft,
)


def _decision(decision="APPROVED", *, evidence=("ev-1",), limitations=(), clarifications=()):
    packet = None
    if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"}:
        packet = build_approved_response_packet(
            packet_id="packet-1", approved_finding_ids=("finding-1",), approved_evidence_ids=evidence,
            limitation_ids=("lim-1",) if limitations else (),
        )
    return DecisionGateOutput(
        contract_version="1.0", request_id="req-1", decision_id="dec-1", decision=decision,
        finding_dispositions=(), safety_issues=(), clarifications=tuple(clarifications), blocked_content=(),
        response_packet=packet, limitations=tuple(limitations), human_review_reasons=(), confidence=0.9,
        decision_trace=(),
    )


def _explanation(*sections, status="DRAFTED", limitations=(), audience="CUSTOMER"):
    return ExplanationGeneratorOutput(
        contract_version="1.0", request_id="req-1", explanation_id="exp-1", audience=audience,
        reading_level="SIMPLE", explanation_mode="PLAIN_LANGUAGE" if status != "CLARIFICATION_DRAFTED" else "CLARIFICATION_REQUEST",
        sections=tuple(sections), terminology_substitutions=(), fidelity_checks=(), fidelity_status="VERIFIED",
        limitations=tuple(limitations), explanation_status=status, confidence=0.88, explanation_trace=(),
    )


def _section(section_id="exp-sec-1", section_type="DIRECT_ANSWER", text="You bear 10% when the condition applies.", **kwargs):
    values = dict(
        section_id=section_id, section_type=section_type, status="DRAFTED", text=text,
        approved_finding_ids=("finding-1",), evidence_ids=("ev-1",), limitation_ids=(), clarification_ids=(),
    )
    values.update(kwargs)
    return explanation_section(**values)


def _input(explanation, decision="APPROVED", context=None, decision_output=None):
    return ResponseAssemblerInput(
        contract_version="1.0", request_id="req-1",
        decision_output=decision_output or _decision(decision), explanation_output=explanation,
        response_format="STANDARD", assembly_context=dict(context or {}),
    )


def _answer_format(**overrides):
    values = dict(
        format_id="answer-v1", format_version="1.0", response_format="STANDARD", audiences=("CUSTOMER",),
        response_statuses=("ANSWER", "ANSWER_WITH_LIMITATIONS"),
        section_order=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
        allowed_section_types=("DIRECT_ANSWER", "EXPLANATION", "CONDITION", "LIMITATION", "EVIDENCE"),
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


def _valid():
    input_value = _input(_explanation(_section()))
    definition = _answer_format()
    return input_value, definition, assemble_sections(input_value, definition)


def test_valid_response_is_verified():
    input_value, definition, draft = _valid()
    result = validate_response_draft(input_value, definition, draft)
    assert result.integrity_status == "VERIFIED"
    assert result.verified is True
    assert all(item.status == "PASSED" for item in result.checks)


def test_limitations_produce_verified_with_limitations():
    limitation = "Applicability depends on the documented condition."
    explanation = _explanation(_section(limitation_ids=("lim-1",)), limitations=(limitation,))
    input_value = _input(explanation, decision_output=_decision("APPROVED_WITH_LIMITATIONS", limitations=(limitation,)))
    definition = _answer_format()
    draft = assemble_sections(input_value, definition)
    result = validate_response_draft(input_value, definition, draft)
    assert result.integrity_status == "VERIFIED_WITH_LIMITATIONS"
    assert result.confidence <= 0.9


def test_changed_section_text_fails_unsupported_content():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], text="You always bear 10% on every claim.")
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status == "FAILED_UNSUPPORTED_CONTENT"


def test_invented_direct_answer_fails():
    input_value, definition, draft = _valid()
    result = validate_response_draft(input_value, definition, replace(draft, direct_answer="Buy this policy."))
    assert result.integrity_status == "FAILED_UNSUPPORTED_CONTENT"


def test_unknown_explanation_section_fails_scope():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], explanation_section_ids=("unknown",))
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status == "FAILED_SECTION_SCOPE"


def test_changed_section_type_fails_scope():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], section_type="LIMITATION")
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status == "FAILED_SECTION_SCOPE"


def test_unapproved_finding_fails_scope():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], approved_finding_ids=("finding-2",))
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status == "FAILED_SECTION_SCOPE"


def test_unknown_evidence_reference_fails():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], evidence_reference_ids=("missing-ref",))
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status == "FAILED_EVIDENCE_REFERENCE"


def test_changed_evidence_source_fails():
    input_value, definition, draft = _valid()
    bad_ref = replace(draft.evidence_references[0], source_id="ev-2")
    result = validate_response_draft(input_value, definition, replace(draft, evidence_references=(bad_ref,)))
    assert result.integrity_status == "FAILED_EVIDENCE_REFERENCE"


def test_duplicate_evidence_reference_ids_fail():
    input_value, definition, draft = _valid()
    result = validate_response_draft(
        input_value, definition, replace(draft, evidence_references=(draft.evidence_references[0], draft.evidence_references[0]))
    )
    assert result.integrity_status == "FAILED_EVIDENCE_REFERENCE"


def test_missing_limitation_fails():
    limitation = "Applicability depends on the documented condition."
    explanation = _explanation(_section(limitation_ids=("lim-1",)), limitations=(limitation,))
    input_value = _input(explanation, decision_output=_decision("APPROVED_WITH_LIMITATIONS", limitations=(limitation,)))
    definition = _answer_format()
    draft = assemble_sections(input_value, definition)
    result = validate_response_draft(input_value, definition, replace(draft, limitations=()))
    assert result.integrity_status == "FAILED_LIMITATION_FIDELITY"


def test_missing_assumption_fails():
    input_value = _input(_explanation(_section()), context={"assumptions": ("Treatment occurs in the stated city.",)})
    definition = _answer_format()
    draft = assemble_sections(input_value, definition)
    result = validate_response_draft(input_value, definition, replace(draft, assumptions=()))
    assert result.integrity_status == "FAILED_ASSUMPTION_FIDELITY"


def test_valid_clarification_is_verified():
    clarification = build_clarification_requirement(
        clarification_id="clar-1", topic="copay", question_key="treatment_city",
        reason="Trigger context is missing.", priority="HIGH", required_context_keys=("treatment_city",),
    )
    section = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="Which city will the treatment take place in?", clarification_ids=("clar-1",),
    )
    explanation = _explanation(section, status="CLARIFICATION_DRAFTED")
    input_value = _input(explanation, decision_output=_decision("CLARIFICATION_REQUIRED", clarifications=(clarification,)))
    definition = _clarification_format()
    draft = assemble_sections(input_value, definition)
    result = validate_response_draft(input_value, definition, draft)
    assert result.integrity_status == "VERIFIED"


def test_clarification_with_direct_answer_fails():
    clarification = build_clarification_requirement(
        clarification_id="clar-1", topic="copay", question_key="treatment_city",
        reason="Trigger context is missing.", priority="HIGH", required_context_keys=("treatment_city",),
    )
    section = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="Which city will the treatment take place in?", clarification_ids=("clar-1",),
    )
    explanation = _explanation(section, status="CLARIFICATION_DRAFTED")
    input_value = _input(explanation, decision_output=_decision("CLARIFICATION_REQUIRED", clarifications=(clarification,)))
    definition = _clarification_format()
    draft = assemble_sections(input_value, definition)
    result = validate_response_draft(input_value, definition, replace(draft, direct_answer="It applies."))
    assert result.integrity_status == "FAILED_CLARIFICATION_SCOPE"


def test_clarification_with_evidence_fails():
    clarification = build_clarification_requirement(
        clarification_id="clar-1", topic="copay", question_key="treatment_city",
        reason="Trigger context is missing.", priority="HIGH", required_context_keys=("treatment_city",),
    )
    section = explanation_section(
        section_id="clar-sec", section_type="CLARIFICATION", status="DRAFTED",
        text="Which city will the treatment take place in?", clarification_ids=("clar-1",),
    )
    explanation = _explanation(section, status="CLARIFICATION_DRAFTED")
    input_value = _input(explanation, decision_output=_decision("CLARIFICATION_REQUIRED", clarifications=(clarification,)))
    definition = _clarification_format()
    draft = assemble_sections(input_value, definition)
    ref = build_evidence_reference(reference_id="ref-x", reference_type="EVIDENCE", source_id="ev-1", label="Evidence")
    result = validate_response_draft(input_value, definition, replace(draft, evidence_references=(ref,)))
    assert result.integrity_status == "FAILED_EVIDENCE_REFERENCE"


def test_wrong_format_definition_fails_decision_match():
    input_value, _, draft = _valid()
    wrong = _answer_format(response_format="COMPACT")
    result = validate_response_draft(input_value, wrong, draft)
    assert result.integrity_status == "FAILED_DECISION_MISMATCH"


def test_section_word_limit_failure():
    input_value, definition, draft = _valid()
    changed = replace(draft.sections[0], text="word " * (definition.max_section_words + 1))
    result = validate_response_draft(input_value, definition, replace(draft, sections=(changed,)))
    assert result.integrity_status in {"FAILED_UNSUPPORTED_CONTENT", "FAILED_FORMAT_LIMIT"}
    assert any(item.check_type == "FORMAT_LIMIT" and item.status == "FAILED" for item in result.checks)


def test_too_many_sections_fails_format_limit():
    input_value, definition, draft = _valid()
    many = tuple(replace(draft.sections[0], section_id=f"sec-{index}") for index in range(definition.max_sections + 1))
    result = validate_response_draft(input_value, definition, replace(draft, sections=many))
    assert any(item.check_type == "FORMAT_LIMIT" and item.status == "FAILED" for item in result.checks)


def test_wrong_order_fails_ordering():
    first = _section(section_id="a", section_type="DIRECT_ANSWER")
    second = _section(section_id="b", section_type="CONDITION", text="The condition applies in specified cities.")
    input_value = _input(_explanation(first, second))
    definition = _answer_format()
    draft = assemble_sections(input_value, definition)
    reversed_draft = replace(draft, sections=tuple(reversed(draft.sections)))
    result = validate_response_draft(input_value, definition, reversed_draft)
    assert result.integrity_status == "FAILED_ORDERING"


def test_duplicate_section_ids_fail_ordering():
    input_value, definition, draft = _valid()
    duplicate = (draft.sections[0], draft.sections[0])
    result = validate_response_draft(input_value, definition, replace(draft, sections=duplicate))
    assert result.integrity_status == "FAILED_ORDERING"


def test_validation_is_deterministic():
    input_value, definition, draft = _valid()
    assert validate_response_draft(input_value, definition, draft) == validate_response_draft(input_value, definition, draft)


def test_validation_does_not_mutate_inputs():
    input_value, definition, draft = _valid()
    before = (input_value, definition, draft)
    validate_response_draft(input_value, definition, draft)
    assert before == (input_value, definition, draft)


def test_result_is_frozen():
    input_value, definition, draft = _valid()
    result = validate_response_draft(input_value, definition, draft)
    with pytest.raises(FrozenInstanceError):
        result.confidence = 0.1  # type: ignore[misc]


def test_rejects_invalid_input_types():
    input_value, definition, draft = _valid()
    with pytest.raises(ResponseIntegrityError):
        validate_response_draft(object(), definition, draft)  # type: ignore[arg-type]
    with pytest.raises(ResponseIntegrityError):
        validate_response_draft(input_value, object(), draft)  # type: ignore[arg-type]
    with pytest.raises(ResponseIntegrityError):
        validate_response_draft(input_value, definition, object())  # type: ignore[arg-type]
