from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)


def _style_registry() -> ExplanationStyleRegistry:
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id="customer-simple-plain-language-v1",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE", "DETAILED"),
        ),
    ))


def _direct_fact():
    return build_finding(
        finding_id="finding-direct-fact",
        requirement_id="requirement-direct-fact",
        finding_type="DOCUMENTED_FACT",
        subject="governed_binding:product_option_36_months",
        predicate="documents",
        object_or_effect="Continuity credit follows prior coverage.",
        condition=None,
        scope="product",
        finding_status="SUPPORTED",
        derivation_type="DIRECT_FACT",
        rule_id="direct_documented_fact_v1",
        rule_version="1.0",
        evidence_ids=("evidence-direct-fact",),
        confidence=1.0,
    )


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-direct-fact",
        approved_finding_ids=("finding-direct-fact",),
        approved_evidence_ids=("evidence-direct-fact",),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-direct-fact",
        disposition="APPROVED",
        basis="Supported by governed evidence.",
        approved_evidence_ids=("evidence-direct-fact",),
        confidence=1.0,
    )
    return build_decision_output(
        request_id="request-direct-fact",
        decision_id="decision-direct-fact",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=1.0,
    )


def _generate(mode: str):
    finding = _direct_fact()
    return generate_explanation(
        explanation_input=build_explanation_input(
            request_id="request-direct-fact",
            decision_output=_decision(),
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_mode=mode,
        ),
        findings_by_id={finding.finding_id: finding},
        style_registry=_style_registry(),
    )


def test_plain_direct_fact_does_not_render_opaque_governed_subject_as_semantics():
    result = _generate("PLAIN_LANGUAGE")

    assert result.explanation_status == "DRAFTED"
    assert result.fidelity_status == "VERIFIED"
    drafted_text = " ".join(section.text for section in result.sections if section.status == "DRAFTED")
    assert "Continuity credit follows prior coverage." in drafted_text
    assert "governed_binding" not in drafted_text
    assert "36" not in drafted_text
    assert any(
        check.check_type == "NO_NEW_FACTS" and check.status == "PASSED"
        for check in result.fidelity_checks
    )


def test_detailed_direct_fact_preserves_same_subject_boundary():
    result = _generate("DETAILED")

    assert result.explanation_status == "DRAFTED"
    assert result.fidelity_status == "VERIFIED"
    drafted_text = " ".join(section.text for section in result.sections if section.status == "DRAFTED")
    assert "Continuity credit follows prior coverage." in drafted_text
    assert "governed_binding" not in drafted_text
    assert "36" not in drafted_text
