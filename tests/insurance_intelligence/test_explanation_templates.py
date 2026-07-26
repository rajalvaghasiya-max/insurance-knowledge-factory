from dataclasses import FrozenInstanceError

import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_clarification_requirement,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.registry import (
    build_style_definition,
    build_terminology_definition,
)
from insurance_intelligence.explanation.templates import (
    ExplanationTemplateError,
    render_explanation_templates,
)


def finding(*, finding_id="finding-1", condition="treatment occurs in the specified city category", limitations=("limitation-1",)):
    return build_finding(
        finding_id=finding_id,
        requirement_id="requirement-1",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of the admissible claim amount",
        condition=condition,
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence-1",),
        limitations=limitations,
        confidence=0.95,
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
        basis="Supported with condition preserved.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        confidence=0.95,
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


def clarification_decision():
    clarification = build_clarification_requirement(
        clarification_id="clarification-1",
        topic="conditional_copayment",
        question_key="trigger_status",
        reason="Please confirm whether the documented trigger applies.",
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


def style(*, audience="CUSTOMER", reading_level="SIMPLE", modes=("PLAIN_LANGUAGE", "CLAUSE_MEANING"), max_words=120):
    return build_style_definition(
        style_id="customer-simple-v1",
        style_version="1.0",
        audience=audience,
        reading_level=reading_level,
        explanation_modes=modes,
        max_section_words=max_words,
    )


def render(**kwargs):
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        audience=kwargs.pop("audience", "CUSTOMER"),
        reading_level=kwargs.pop("reading_level", "SIMPLE"),
        explanation_mode=kwargs.pop("mode", "PLAIN_LANGUAGE"),
    )
    return render_explanation_templates(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style=kwargs.pop("style_value", style()),
        terminology=kwargs.pop("terminology", ()),
    )


def test_plain_language_preserves_percentage_condition_and_evidence():
    result = render()
    meaning = next(item for item in result.sections if item.section_type == "MEANING")
    assert "10%" in meaning.text
    assert "specified city category" in meaning.text
    assert meaning.evidence_ids == ("evidence-1",)


def test_customer_subject_is_rendered_as_you():
    result = render()
    assert "you must bear" in result.sections[0].text.lower()


def test_condition_gets_dedicated_section():
    result = render()
    condition = next(item for item in result.sections if item.section_type == "CONDITION")
    assert condition.approved_finding_ids == ("finding-1",)


def test_limitation_notice_is_preserved():
    result = render()
    limitation = next(item for item in result.sections if item.section_type == "LIMITATION")
    assert limitation.limitation_ids == ("limitation-1",)


def test_evidence_note_is_preserved():
    result = render()
    note = next(item for item in result.sections if item.section_type == "EVIDENCE_NOTE")
    assert note.evidence_ids == ("evidence-1",)


def test_terminology_substitution_is_recorded():
    term = build_terminology_definition(
        terminology_id="admissible-simple",
        terminology_version="1.0",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        audience="CUSTOMER",
        reading_levels=("SIMPLE",),
        explanation_modes=("PLAIN_LANGUAGE",),
    )
    result = render(terminology=(term,))
    assert "eligible claim amount" in result.sections[0].text
    assert result.terminology_substitutions[0].meaning_preserved is True


def test_nonmatching_terminology_is_not_applied():
    term = build_terminology_definition(
        terminology_id="advisor-only",
        terminology_version="1.0",
        source_term="admissible claim amount",
        rendered_term="eligible claim amount",
        action="SIMPLIFY",
        audience="ADVISOR",
        reading_levels=("SIMPLE",),
        explanation_modes=("PLAIN_LANGUAGE",),
    )
    result = render(terminology=(term,))
    assert result.terminology_substitutions == ()


def test_advisor_talking_point_uses_governed_template():
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        audience="ADVISOR",
        reading_level="STANDARD",
        explanation_mode="ADVISOR_TALKING_POINTS",
    )
    result = render_explanation_templates(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style=style(audience="ADVISOR", reading_level="STANDARD", modes=("ADVISOR_TALKING_POINTS",)),
    )
    assert result.sections[0].section_type == "ADVISOR_TALKING_POINT"
    assert result.sections[0].text.startswith("Explain that")


def test_detailed_mode_preserves_condition():
    item = build_input(
        request_id="request-1",
        decision_output=approved_decision(),
        explanation_mode="DETAILED",
    )
    result = render_explanation_templates(
        explanation_input=item,
        findings_by_id={"finding-1": finding()},
        style=style(modes=("DETAILED",)),
    )
    assert "This applies when" in result.sections[0].text


def test_clarification_decision_produces_only_clarification_section():
    item = build_input(
        request_id="request-1",
        decision_output=clarification_decision(),
        explanation_mode="CLARIFICATION_REQUEST",
    )
    result = render_explanation_templates(
        explanation_input=item,
        findings_by_id={},
        style=style(modes=("CLARIFICATION_REQUEST",)),
    )
    assert len(result.sections) == 1
    assert result.sections[0].section_type == "CLARIFICATION"


def test_communication_context_can_supply_clarification_wording():
    item = build_input(
        request_id="request-1",
        decision_output=clarification_decision(),
        explanation_mode="CLARIFICATION_REQUEST",
        communication_context={"trigger_status": "Did the documented trigger apply to this treatment?"},
    )
    result = render_explanation_templates(
        explanation_input=item,
        findings_by_id={},
        style=style(modes=("CLARIFICATION_REQUEST",)),
    )
    assert result.sections[0].text.startswith("Did the documented trigger")


def test_missing_approved_finding_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationTemplateError, match="missing"):
        render_explanation_templates(explanation_input=item, findings_by_id={}, style=style())


def test_style_audience_mismatch_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationTemplateError, match="does not match"):
        render_explanation_templates(
            explanation_input=item,
            findings_by_id={"finding-1": finding()},
            style=style(audience="ADVISOR"),
        )


def test_style_mode_mismatch_fails_closed():
    item = build_input(request_id="request-1", decision_output=approved_decision())
    with pytest.raises(ExplanationTemplateError, match="does not support"):
        render_explanation_templates(
            explanation_input=item,
            findings_by_id={"finding-1": finding()},
            style=style(modes=("DETAILED",)),
        )


def test_section_word_limit_is_enforced():
    with pytest.raises(ExplanationTemplateError, match="max_section_words"):
        render(style_value=style(max_words=3))


def test_result_is_immutable():
    result = render()
    with pytest.raises(FrozenInstanceError):
        result.template_ids = ()  # type: ignore[misc]


def test_input_finding_is_not_mutated():
    source = finding()
    before = source
    item = build_input(request_id="request-1", decision_output=approved_decision())
    render_explanation_templates(
        explanation_input=item,
        findings_by_id={"finding-1": source},
        style=style(),
    )
    assert source == before


def test_output_is_deterministic():
    first = render()
    second = render()
    assert first == second


def test_no_recommendation_language_is_introduced():
    result = render()
    combined = " ".join(item.text.lower() for item in result.sections)
    assert "should buy" not in combined
    assert "recommended" not in combined


def test_no_rupee_calculation_is_introduced():
    result = render()
    combined = " ".join(item.text for item in result.sections)
    assert "₹" not in combined
    assert "Rs." not in combined


def test_template_ids_are_governed_and_ordered():
    result = render()
    assert result.template_ids == (
        "plain_finding_v1",
        "condition_notice_v1",
        "limitation_notice_v1",
        "evidence_note_v1",
    )
