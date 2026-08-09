from __future__ import annotations

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.evidence import EvidencePackage, Lineage
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.explanation.registry import build_style_definition
from insurance_intelligence.explanation.templates import render_explanation_templates
from insurance_intelligence.reasoning.rules import (
    build_rule_input,
    conditional_copayment_obligation,
)


GOVERNED_STAR_REVIEWED_STATEMENT = (
    "Star Comprehensive applies a 10% co-payment to each and every claim for fresh as well as renewal policies "
    "where the insured person's age at entry is 61 years or above. The co-payment does not apply where the "
    "insured person entered the policy before attaining 61 years of age and renewed continuously without a "
    "break. The policy wording limits this co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, "
    "II.8, II.9, II.10, II.11, II.15 and II.25."
)


def _evidence() -> EvidencePackage:
    return EvidencePackage(
        evidence_id="ev-star-copay-reviewed-statement",
        requirement_id="req-star-copay-template-regression",
        subject_reference="Star Comprehensive",
        governed_entity_reference="star_health:star_comprehensive",
        field_or_topic="conditional_copayment",
        claim=GOVERNED_STAR_REVIEWED_STATEMENT,
        evidence_role="SUPPORTING",
        source_type="POLICY_WORDING",
        document_reference="star-comprehensive-policy-wording",
        document_version="governed-reviewed-statement-v1",
        effective_from=None,
        effective_to=None,
        page=39,
        section="Conditional co-payment",
        source_excerpt=GOVERNED_STAR_REVIEWED_STATEMENT,
        normalized_fact_reference="finding-star-conditional-copay",
        authority_rank=3,
        authority_requirement="AUTHORITATIVE",
        version_status="CURRENT_APPLICABLE",
        applicability_status="APPLICABLE",
        lineage=Lineage(
            "star-comprehensive-policy-wording.pdf",
            "a" * 64,
            "binding.json",
            "b" * 64,
            "binding",
            "projection",
            "VERIFIED",
        ),
        retrieval_basis=("binding", "canonical_projection"),
        confidence=0.98,
    )


def _production_finding():
    rule_input = build_rule_input(
        requirement_id="req-star-copay-template-regression",
        evidence=(_evidence(),),
        approved_context={},
    )
    findings = conditional_copayment_obligation(rule_input)
    assert len(findings) == 1
    return findings[0]


def _explanation_input(finding):
    packet = build_approved_response_packet(
        packet_id="packet-star-copay-template-regression",
        approved_finding_ids=(finding.finding_id,),
        approved_evidence_ids=finding.evidence_ids,
        limitation_ids=finding.limitations,
        prohibited_operations=("RECOMMEND", "RANK"),
    )
    disposition = build_finding_disposition(
        finding_id=finding.finding_id,
        disposition="APPROVED_WITH_LIMITATIONS",
        basis="Governed Star conditional copayment semantics are preserved.",
        approved_evidence_ids=finding.evidence_ids,
        limitation_ids=finding.limitations,
        confidence=finding.confidence,
    )
    decision = build_decision_output(
        request_id="request-star-copay-template-regression",
        decision_id="decision-star-copay-template-regression",
        decision="APPROVED_WITH_LIMITATIONS",
        finding_dispositions=(disposition,),
        response_packet=packet,
        limitations=("Conditional policy semantics must remain explicit.",),
        confidence=finding.confidence,
    )
    return build_input(
        request_id="request-star-copay-template-regression",
        decision_output=decision,
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_mode="PLAIN_LANGUAGE",
    )


def _style():
    return build_style_definition(
        style_id="star-copay-template-regression-v1",
        style_version="1.0",
        audience="CUSTOMER",
        reading_level="SIMPLE",
        explanation_modes=("PLAIN_LANGUAGE",),
        preserve_conditions=True,
        preserve_limitations=True,
        preserve_evidence_notes=True,
        max_section_words=180,
    )


def test_real_governed_star_clause_flows_through_extraction_into_structured_template():
    finding = _production_finding()
    result = render_explanation_templates(
        explanation_input=_explanation_input(finding),
        findings_by_id={finding.finding_id: finding},
        style=_style(),
    )
    meaning = next(section for section in result.sections if section.section_type == "MEANING")

    assert finding.trigger == "where the insured person's age at entry is 61 years or above"
    assert finding.exception == (
        "The co-payment does not apply where the insured person entered the policy before attaining 61 years "
        "of age and renewed continuously without a break"
    )
    assert finding.applicability_scope == (
        "The policy wording limits this co-payment to Sections II.1, II.2, II.3, II.4, II.5, II.6, II.7, "
        "II.8, II.9, II.10, II.11, II.15 and II.25"
    )

    text = meaning.text
    trigger_at = text.index("Trigger:")
    obligation_at = text.index("Obligation:")
    exception_at = text.index("Exception:")
    scope_at = text.index("Scope:")
    assert trigger_at < obligation_at < exception_at < scope_at
    assert "61 years or above" in text
    assert "10% of the admissible claim amount" in text
    assert "entered the policy before attaining 61 years of age" in text
    assert "Sections II.1" in text and "II.25" in text
    assert "When where" not in text
    assert meaning.approved_finding_ids == (finding.finding_id,)
    assert meaning.evidence_ids == ("ev-star-copay-reviewed-statement",)


def test_real_governed_star_clause_renders_deterministically():
    finding = _production_finding()
    explanation_input = _explanation_input(finding)

    first = render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id={finding.finding_id: finding},
        style=_style(),
    )
    second = render_explanation_templates(
        explanation_input=explanation_input,
        findings_by_id={finding.finding_id: finding},
        style=_style(),
    )

    assert first == second
