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


def _finding(effect: str):
    return build_finding(
        finding_id="finding-1",
        requirement_id="requirement-1",
        finding_type="CLAIM_CONDITION",
        subject="claim",
        predicate="has_outcome",
        object_or_effect=effect,
        condition="the documented policy conditions are satisfied",
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id="claim_condition_v1",
        rule_version="1.0",
        evidence_ids=("evidence-1",),
        confidence=0.9,
    )


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("evidence-1",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED",
        basis="Approved for claim-payment safety regression.",
        approved_evidence_ids=("evidence-1",),
        confidence=0.9,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=0.9,
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


def _render(effect: str):
    finding = _finding(effect)
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


@pytest.mark.parametrize(
    "effect",
    (
        "the claim will be paid",
        "the claim is guaranteed",
        "the insurer will pay the claim",
        "the claim will definitely be approved",
    ),
)
def test_claim_payment_prediction_fails_closed(effect):
    with pytest.raises(ExplanationTemplateError, match="claim payment or approval"):
        _render(effect)


def test_claim_condition_without_payment_prediction_remains_renderable():
    result = _render("the co-payment rule affects the insured's share of an admissible claim amount")
    meaning = next(section for section in result.sections if section.section_type == "MEANING")
    assert "co-payment rule affects" in meaning.text
    assert "will be paid" not in meaning.text.lower()
    assert "guaranteed" not in meaning.text.lower()
