from __future__ import annotations

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)


FINDING_ID = "finding:aditya_birla_health:activ_one_nxt:super_reload"
POLICY_EVIDENCE_ID = "ev_activ_one_nxt_super_reload_policy_wording"
PROSPECTUS_EVIDENCE_ID = "ev_activ_one_nxt_super_reload_prospectus"
LIMITATION_ID = "limitation:activ_one_nxt:super_reload:variant_schedule"


def _restoration_finding():
    return build_finding(
        finding_id=FINDING_ID,
        requirement_id="requirement:restoration",
        finding_type="COVERAGE_EFFECT",
        subject="Activ One NXT Super Reload",
        predicate="restores",
        object_or_effect="100% of the Base Sum Insured per activation, with unlimited activations during the Policy Year",
        condition=(
            "the underlying claim is admissible and the Base Sum Insured plus accumulated Super Credit, "
            "if applicable, is exhausted or insufficient for the claim"
        ),
        scope="aditya_birla_health:activ_one:nxt",
        finding_status="SUPPORTED_WITH_LIMITATIONS",
        derivation_type="DETERMINISTIC_DERIVATION",
        rule_id="activ_one_nxt_super_reload_v1",
        rule_version="1.0",
        evidence_ids=(POLICY_EVIDENCE_ID, PROSPECTUS_EVIDENCE_ID),
        limitations=(
            "Maximum liability from Super Reload under a single claim is the Base Sum Insured.",
            "Variant applicability and in-force benefits remain controlled by the Policy Schedule.",
            "This finding does not establish claim entitlement or guarantee claim payment.",
        ),
        confidence=0.95,
    )


def _decision_output():
    packet = build_approved_response_packet(
        packet_id="packet:activ_one_nxt:super_reload",
        approved_finding_ids=(FINDING_ID,),
        approved_evidence_ids=(POLICY_EVIDENCE_ID, PROSPECTUS_EVIDENCE_ID),
        limitation_ids=(LIMITATION_ID,),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id=FINDING_ID,
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="Supported by governed Super Reload policy wording and prospectus evidence.",
        approved_evidence_ids=(POLICY_EVIDENCE_ID, PROSPECTUS_EVIDENCE_ID),
        limitation_ids=(LIMITATION_ID,),
        confidence=0.95,
    )
    return build_decision_output(
        request_id="request:hg5:activ_one_nxt:super_reload",
        decision_id="decision:hg5:activ_one_nxt:super_reload",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=(
            "Explain only the governed benefit mechanics; do not infer claim entitlement or payment.",
        ),
        confidence=0.95,
    )


def _styles() -> ExplanationStyleRegistry:
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id="style:hg5:customer:simple",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE",),
            max_section_words=140,
            priority=10,
        ),
    ))


def _generate():
    explanation_input = build_input(
        request_id="request:hg5:activ_one_nxt:super_reload",
        decision_output=_decision_output(),
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
        communication_context={"domain_scope": "HEALTH"},
    )
    return generate_explanation(
        explanation_input=explanation_input,
        findings_by_id={FINDING_ID: _restoration_finding()},
        style_registry=_styles(),
    )


def test_hg5_restoration_explanation_is_drafted_with_limitations() -> None:
    result = _generate()

    assert result.explanation_status == "DRAFTED_WITH_LIMITATIONS"
    assert result.fidelity_status == "VERIFIED_WITH_LIMITATIONS"
    assert result.sections


def test_hg5_restoration_explanation_preserves_effect_and_trigger() -> None:
    result = _generate()
    text = " ".join(section.text for section in result.sections)

    assert "100%" in text
    assert "Base Sum Insured" in text
    assert "unlimited" in text
    assert "exhausted or insufficient" in text


def test_hg5_restoration_explanation_preserves_evidence_lineage() -> None:
    result = _generate()
    linked = {evidence_id for section in result.sections for evidence_id in section.evidence_ids}

    assert POLICY_EVIDENCE_ID in linked
    assert PROSPECTUS_EVIDENCE_ID in linked


def test_hg5_restoration_explanation_preserves_approved_limitation_boundary() -> None:
    result = _generate()
    limitation_sections = [section for section in result.sections if section.section_type == "LIMITATION"]

    assert result.explanation_status == "DRAFTED_WITH_LIMITATIONS"
    assert result.fidelity_status == "VERIFIED_WITH_LIMITATIONS"
    assert len(limitation_sections) == 1
    assert limitation_sections[0].limitation_ids == (LIMITATION_ID,)
    assert "limitations remain" in limitation_sections[0].text.casefold()


def test_hg5_unapproved_finding_limitation_prose_is_not_silently_rendered() -> None:
    result = _generate()
    text = " ".join(section.text for section in result.sections).casefold()

    assert "maximum liability from super reload" not in text
    assert "variant applicability and in-force benefits" not in text
    assert "does not establish claim entitlement" not in text


def test_hg5_restoration_explanation_does_not_recommend_or_guarantee_payment() -> None:
    result = _generate()
    text = " ".join(section.text for section in result.sections).casefold()

    forbidden = (
        "you should buy",
        "recommended product",
        "best product",
        "claim will be paid",
        "claim is guaranteed",
        "guaranteed payment",
    )
    assert all(phrase not in text for phrase in forbidden)


def test_hg5_explanation_output_has_no_recommendation_or_final_answer_fields() -> None:
    result = _generate()

    assert not hasattr(result, "recommendation")
    assert not hasattr(result, "final_answer")
