import pytest

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.registry import build_style_definition
from insurance_intelligence.explanation.templates import (
    ExplanationTemplateError,
    render_explanation_templates,
)


def _finding(status: str):
    limitations = ("limitation-1",) if status in {"SUPPORTED_WITH_LIMITATIONS", "PARTIALLY_SUPPORTED"} else ()
    return build_finding(
        finding_id="finding-1",
        requirement_id="requirement-1",
        finding_type="CLAIM_COST_SHARING",
        subject="insured",
        predicate="must_bear",
        object_or_effect="10% of the admissible claim amount",
        condition="the documented trigger applies",
        scope="star_health:star_comprehensive",
        finding_status=status,
        derivation_type="CONDITIONAL_DERIVATION",
        rule_id="conditional_copayment_obligation_v1",
        rule_version="1.0",
        evidence_ids=("evidence-1",),
        limitations=limitations,
        confidence=0.8,
    )


def _decision():
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
        basis="Approved only for status-sensitive explanation regression.",
        approved_evidence_ids=("evidence-1",),
        limitation_ids=("limitation-1",),
        confidence=0.8,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Status and limitations must remain explicit.",),
        confidence=0.8,
    )


def _style():
    return build_style_definition(
        style_id="customer-simple-v1",
        style_version="1.0",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_modes=("PLAIN_LANGUAGE",),
        max_section_words=120,
    )


def _render(status: str):
    finding = _finding(status)
    explanation_input = build_input(
        request_id="request-1",
        decision_output=_decision(),
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
    )
    return render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id={finding.finding_id: finding},
        style=_style(),
    )


def test_supported_finding_keeps_definitive_existing_wording():
    result = _render("SUPPORTED")
    meaning = next(section for section in result.sections if section.section_type == "MEANING")

    assert meaning.text.startswith("Trigger:")
    assert "partially supported" not in meaning.text.lower()
    assert "supported with limitations" not in meaning.text.lower()


def test_partially_supported_finding_explicitly_qualifies_certainty():
    result = _render("PARTIALLY_SUPPORTED")
    meaning = next(section for section in result.sections if section.section_type == "MEANING")

    assert meaning.text.startswith("This finding is only partially supported by the approved evidence.")
    assert "10% of the admissible claim amount" in meaning.text
    assert "Trigger:" in meaning.text


def test_supported_with_limitations_finding_explicitly_qualifies_language():
    result = _render("SUPPORTED_WITH_LIMITATIONS")
    meaning = next(section for section in result.sections if section.section_type == "MEANING")

    assert meaning.text.startswith("This finding is supported with limitations.")
    assert "10% of the admissible claim amount" in meaning.text


@pytest.mark.parametrize("status", ("CONFLICTING", "UNSUPPORTED", "BLOCKED"))
def test_non_renderable_finding_statuses_fail_closed(status):
    with pytest.raises(ExplanationTemplateError, match="not eligible for explanation rendering"):
        _render(status)
