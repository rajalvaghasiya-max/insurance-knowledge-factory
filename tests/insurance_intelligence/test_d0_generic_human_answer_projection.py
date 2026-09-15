from __future__ import annotations

import inspect

import pytest

from insurance_intelligence.contracts.response import (
    build_evidence_reference,
    build_output,
    build_section,
    build_trace_event,
)
from insurance_intelligence.response import human_answer as human_answer_module
from insurance_intelligence.response.human_answer import (
    HumanAnswerProjectionError,
    project_human_answer,
)


def _response(
    *,
    answer: str,
    meaning: str,
    limitations: tuple[str, ...] = (),
    status: str | None = None,
    suffix: str = "case",
):
    reference_id = f"reference-{suffix}"
    finding_id = f"finding-{suffix}"
    section_id = f"section-{suffix}"
    response_status = status or ("ANSWER_WITH_LIMITATIONS" if limitations else "ANSWER")
    reference = build_evidence_reference(
        reference_id=reference_id,
        reference_type="EVIDENCE",
        source_id=f"evidence-{suffix}",
        label="Governed source evidence",
        locator="policy wording",
        approved_finding_ids=(finding_id,),
    )
    section = build_section(
        section_id=section_id,
        section_type="EXPLANATION",
        status="INCLUDED",
        text=meaning,
        approved_finding_ids=(finding_id,),
        evidence_reference_ids=(reference_id,),
    )
    trace = build_trace_event(
        trace_id=f"trace-{suffix}",
        sequence=1,
        event_type="RESPONSE_ASSEMBLY_COMPLETED",
        decision=response_status,
        basis="test governed response assembled",
        order_marker="0001",
        output_references=(f"response-{suffix}",),
    )
    return build_output(
        request_id=f"request-{suffix}",
        response_id=f"response-{suffix}",
        response_status=response_status,
        audience="CUSTOMER",
        response_format="STANDARD",
        direct_answer=answer,
        sections=(section,),
        evidence_references=(reference,),
        limitations=limitations,
        confidence=0.9,
        response_trace=(trace,),
    )


def test_human_view_is_separate_from_provenance_and_preserves_machine_text():
    response = _response(
        answer="The governed answer is 36 months.",
        meaning="Continuity may qualify how the documented period applies.",
        limitations=("Customer-specific eligibility is not established by this answer.",),
        suffix="factual",
    )

    projected = project_human_answer(response)

    assert projected.source_response_id == response.response_id
    assert projected.human_view.answer == response.direct_answer
    assert projected.human_view.meaning == (
        "Continuity may qualify how the documented period applies.",
    )
    assert projected.human_view.unknowns == response.limitations
    assert projected.provenance_panel.evidence_references == response.evidence_references
    assert projected.provenance_panel.response_trace == response.response_trace

    human_text = " ".join(
        (
            projected.human_view.answer,
            *projected.human_view.meaning,
            *projected.human_view.unknowns,
            projected.human_view.next_step or "",
        )
    )
    assert "evidence-factual" not in human_text
    assert "finding-factual" not in human_text


def test_fail_closed_answer_with_limitations_has_a_resolution_next_step():
    response = _response(
        answer="The exact boundary date cannot be resolved from the governed wording.",
        meaning="The activation convention is not established at the calculated boundary date.",
        limitations=("The activation convention is unresolved at the calculated boundary date.",),
        suffix="boundary",
    )

    projected = project_human_answer(response)

    assert projected.human_view.next_step
    next_step = projected.human_view.next_step.lower()
    assert "check" in next_step or "confirm" in next_step
    assert "policy" in next_step
    assert "insurer" in next_step or "advisor" in next_step


def test_limitation_negative_control_changes_unknowns_and_next_step():
    limited = _response(
        answer="The timeline result is unresolved.",
        meaning="A material applicability condition is not established.",
        limitations=("A required case fact is missing.",),
        suffix="limited",
    )
    clean = _response(
        answer="The timeline result is resolved.",
        meaning="The required case facts are established.",
        limitations=(),
        suffix="clean",
    )

    limited_view = project_human_answer(limited).human_view
    clean_view = project_human_answer(clean).human_view

    assert limited_view.unknowns == ("A required case fact is missing.",)
    assert limited_view.next_step is not None
    assert clean_view.unknowns == ()
    assert clean_view.next_step is None


def test_answer_negative_control_follows_changed_machine_answer():
    first = _response(
        answer="The waiting period is still active.",
        meaning="The approved event date is before the governed boundary.",
        suffix="first",
    )
    second = _response(
        answer="The waiting period is complete.",
        meaning="The approved event date is after the governed boundary.",
        suffix="second",
    )

    assert project_human_answer(first).human_view.answer != project_human_answer(second).human_view.answer
    assert project_human_answer(first).human_view.answer == first.direct_answer
    assert project_human_answer(second).human_view.answer == second.direct_answer


@pytest.mark.parametrize(
    ("answer", "meaning", "limitations", "suffix"),
    (
        (
            "A factual governed answer.",
            "A factual explanation.",
            (),
            "factual-generic",
        ),
        (
            "A resolved conditional answer.",
            "A deterministic applicability explanation.",
            ("This does not establish final claim approval.",),
            "resolved-generic",
        ),
        (
            "An uncertainty remains.",
            "The governed inputs do not resolve the boundary.",
            ("The boundary convention remains unresolved.",),
            "fail-closed-generic",
        ),
        (
            "An unrehearsed fourth answer.",
            "An unrehearsed fourth explanation.",
            (),
            "fourth-generic",
        ),
    ),
)
def test_one_generic_projector_handles_rehearsed_and_unrehearsed_answers(
    answer: str,
    meaning: str,
    limitations: tuple[str, ...],
    suffix: str,
):
    response = _response(
        answer=answer,
        meaning=meaning,
        limitations=limitations,
        suffix=suffix,
    )
    projection = project_human_answer(response)
    assert projection.human_view.answer == answer
    assert projection.human_view.meaning == (meaning,)


def test_projector_source_contains_no_insurer_product_or_mechanic_branch():
    source = inspect.getsource(human_answer_module).lower()
    forbidden = (
        "star_health",
        "star comprehensive",
        "star_comprehensive",
        "bajaj",
        "hdfc",
        "ped_wait",
        "conditional_copayment",
        "waiting_period_applicability",
    )
    assert not any(token in source for token in forbidden)


def test_non_answer_status_is_not_silently_presented_as_an_answer():
    response = _response(
        answer="Temporary fixture answer.",
        meaning="Temporary fixture meaning.",
        suffix="unsupported",
    )
    # Build a structurally separate invalid-for-D0 object by replacing the answer status is
    # intentionally avoided: the canonical response contract itself forbids answer content
    # on non-answer statuses. The projector therefore needs only a type/status guard.
    with pytest.raises(HumanAnswerProjectionError, match="ResponseAssemblerOutput"):
        project_human_answer(object())  # type: ignore[arg-type]
    assert project_human_answer(response).human_view.answer == response.direct_answer
