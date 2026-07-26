from dataclasses import FrozenInstanceError, fields

import pytest

from insurance_intelligence.contracts import response as rc
from insurance_intelligence.contracts.explanation import build_output as build_explanation_output
from insurance_intelligence.contracts.decision import build_output as build_decision_output


def _decision(decision="APPROVED"):
    # Contract input tests only require runtime type and request identity; construct without invoking
    # deep decision validation to keep this unit isolated from gate fixtures.
    from insurance_intelligence.contracts.decision import DecisionGateOutput

    return DecisionGateOutput(
        contract_version="1.0",
        request_id="req-1",
        decision_id="dec-1",
        decision=decision,
        finding_dispositions=(),
        safety_issues=(),
        clarifications=(),
        blocked_content=(),
        response_packet=object() if decision in {"APPROVED", "APPROVED_WITH_LIMITATIONS"} else None,
        limitations=(),
        human_review_reasons=(),
        confidence=0.9,
        decision_trace=(),
    )


def _explanation(status="DRAFTED", mode="PLAIN_LANGUAGE"):
    from insurance_intelligence.contracts.explanation import ExplanationGeneratorOutput

    return ExplanationGeneratorOutput(
        contract_version="1.0",
        request_id="req-1",
        explanation_id="exp-1",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode=mode,
        sections=(),
        terminology_substitutions=(),
        fidelity_checks=(),
        fidelity_status="VERIFIED",
        limitations=(),
        explanation_status=status,
        confidence=0.9,
        explanation_trace=(),
    )


def _section(**overrides):
    values = dict(
        section_id="sec-1",
        section_type="DIRECT_ANSWER",
        status="INCLUDED",
        text="When the condition applies, you bear 10% of the eligible claim amount.",
        explanation_section_ids=("exp-sec-1",),
        approved_finding_ids=("finding-1",),
        evidence_reference_ids=("ref-1",),
    )
    values.update(overrides)
    return rc.build_section(**values)


def _reference(**overrides):
    values = dict(
        reference_id="ref-1",
        reference_type="EVIDENCE",
        source_id="ev-1",
        label="Policy wording, page 39",
        locator="page 39",
        approved_finding_ids=("finding-1",),
    )
    values.update(overrides)
    return rc.build_evidence_reference(**values)


def test_build_input_accepts_approved_draft():
    value = rc.build_input(request_id="req-1", decision_output=_decision(), explanation_output=_explanation())
    assert value.response_format == "STANDARD"
    assert value.assembly_context == {}


def test_build_input_copies_context():
    context = {"channel": "chat"}
    value = rc.build_input(
        request_id="req-1", decision_output=_decision(), explanation_output=_explanation(), assembly_context=context
    )
    context["channel"] = "changed"
    assert value.assembly_context == {"channel": "chat"}


def test_build_input_rejects_request_mismatch():
    with pytest.raises(rc.ResponseContractError, match="decision_output"):
        rc.build_input(request_id="other", decision_output=_decision(), explanation_output=_explanation())


def test_build_input_rejects_approved_without_draft():
    with pytest.raises(rc.ResponseContractError, match="drafted explanation"):
        rc.build_input(
            request_id="req-1",
            decision_output=_decision(),
            explanation_output=_explanation(status="WITHHELD"),
        )


def test_build_input_accepts_clarification_pair():
    value = rc.build_input(
        request_id="req-1",
        decision_output=_decision("CLARIFICATION_REQUIRED"),
        explanation_output=_explanation(status="CLARIFICATION_DRAFTED", mode="CLARIFICATION_REQUEST"),
    )
    assert value.decision_output.decision == "CLARIFICATION_REQUIRED"


def test_build_input_rejects_ineligible_decision():
    with pytest.raises(rc.ResponseContractError, match="not eligible"):
        rc.build_input(
            request_id="req-1",
            decision_output=_decision("BLOCKED"),
            explanation_output=_explanation(),
        )


def test_build_section_requires_evidence_for_findings():
    with pytest.raises(rc.ResponseContractError, match="preserve evidence"):
        _section(evidence_reference_ids=())


def test_build_section_requires_clarification_ids():
    with pytest.raises(rc.ResponseContractError, match="clarification IDs"):
        _section(section_type="CLARIFICATION", approved_finding_ids=(), evidence_reference_ids=())


def test_nonclarification_section_rejects_clarification_ids():
    with pytest.raises(rc.ResponseContractError, match="only clarification"):
        _section(clarification_ids=("clar-1",))


def test_section_is_frozen():
    value = _section()
    with pytest.raises(FrozenInstanceError):
        value.text = "changed"  # type: ignore[misc]


def test_evidence_reference_validates_type():
    with pytest.raises(rc.ResponseContractError, match="reference_type"):
        _reference(reference_type="UNKNOWN")


def test_trace_requires_positive_sequence():
    with pytest.raises(rc.ResponseContractError, match="positive integer"):
        rc.build_trace_event(
            trace_id="tr-1", sequence=0, event_type="INPUT_VALIDATED", decision="OK", basis="valid", order_marker="001"
        )


def test_answer_output_is_valid():
    output = rc.build_output(
        request_id="req-1",
        response_id="resp-1",
        response_status="ANSWER",
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer="The 10% share applies only when the documented condition applies.",
        sections=(_section(),),
        evidence_references=(_reference(),),
        confidence=0.9,
    )
    assert output.response_status == "ANSWER"


def test_answer_requires_direct_answer():
    with pytest.raises(rc.ResponseContractError, match="direct answer"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", sections=(_section(),), evidence_references=(_reference(),)
        )


def test_answer_with_limitations_requires_limitations():
    with pytest.raises(rc.ResponseContractError, match="requires limitations"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER_WITH_LIMITATIONS",
            audience="CUSTOMER", response_format="STANDARD", direct_answer="Conditional answer.",
            sections=(_section(),), evidence_references=(_reference(),)
        )


def test_answer_rejects_clarification_questions():
    with pytest.raises(rc.ResponseContractError, match="clarification questions"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Answer", sections=(_section(),),
            evidence_references=(_reference(),), clarification_questions=("Where was treatment taken?",)
        )


def test_clarification_output_is_valid():
    section = _section(
        section_type="CLARIFICATION", text="Which city was the treatment taken in?",
        approved_finding_ids=(), evidence_reference_ids=(), clarification_ids=("clar-1",)
    )
    output = rc.build_output(
        request_id="req-1", response_id="resp-1", response_status="CLARIFICATION_REQUIRED",
        audience="CUSTOMER", response_format="STANDARD", sections=(section,),
        clarification_questions=("Which city was the treatment taken in?",), confidence=0.8
    )
    assert output.direct_answer is None


def test_clarification_rejects_evidence_exposure():
    section = _section(
        section_type="CLARIFICATION", text="Which city?", approved_finding_ids=(),
        evidence_reference_ids=(), clarification_ids=("clar-1",)
    )
    with pytest.raises(rc.ResponseContractError, match="cannot expose evidence"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="CLARIFICATION_REQUIRED",
            audience="CUSTOMER", response_format="STANDARD", sections=(section,),
            evidence_references=(_reference(),), clarification_questions=("Which city?",)
        )


def test_nonanswer_status_rejects_content():
    with pytest.raises(rc.ResponseContractError, match="cannot expose"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="BLOCKED", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Hidden answer", sections=(_section(),),
            evidence_references=(_reference(),)
        )


def test_unknown_evidence_reference_is_rejected():
    with pytest.raises(rc.ResponseContractError, match="unknown evidence"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Answer", sections=(_section(),), evidence_references=()
        )


def test_duplicate_section_ids_are_rejected():
    with pytest.raises(rc.ResponseContractError, match="section IDs"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Answer", sections=(_section(), _section()),
            evidence_references=(_reference(),)
        )


def test_trace_order_is_enforced():
    first = rc.build_trace_event(
        trace_id="tr-2", sequence=2, event_type="RESPONSE_VALIDATED", decision="OK", basis="valid", order_marker="002"
    )
    second = rc.build_trace_event(
        trace_id="tr-1", sequence=1, event_type="INPUT_VALIDATED", decision="OK", basis="valid", order_marker="001"
    )
    with pytest.raises(rc.ResponseContractError, match="unique and ordered"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Answer", sections=(_section(),),
            evidence_references=(_reference(),), response_trace=(first, second)
        )


def test_trace_rejects_unknown_section():
    event = rc.build_trace_event(
        trace_id="tr-1", sequence=1, event_type="RESPONSE_SECTION_CREATED", decision="CREATED",
        basis="approved", order_marker="001", section_id="missing"
    )
    with pytest.raises(rc.ResponseContractError, match="unknown section"):
        rc.build_output(
            request_id="req-1", response_id="resp-1", response_status="ANSWER", audience="CUSTOMER",
            response_format="STANDARD", direct_answer="Answer", sections=(_section(),),
            evidence_references=(_reference(),), response_trace=(event,)
        )


def test_output_has_no_new_reasoning_or_recommendation_fields():
    names = {item.name for item in fields(rc.ResponseAssemblerOutput)}
    assert "recommendation" not in names
    assert "reasoning" not in names
    assert "example" not in names
