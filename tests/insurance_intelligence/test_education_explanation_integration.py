from __future__ import annotations

from dataclasses import replace

from insurance_intelligence.contracts.decision import (
    build_approved_response_packet,
    build_finding_disposition,
    build_output as build_decision_output,
)
from insurance_intelligence.contracts.education_publication import (
    CUSTOMER_EDUCATION,
    EDUCATION_PUBLICATION_STATUS,
    EducationExample,
    EducationPublicationRecord,
)
from insurance_intelligence.contracts.explanation import build_input as build_explanation_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.contracts.response import build_input as build_response_input
from insurance_intelligence.explanation.education import render_education_sections
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.validator import validate_explanation_fidelity
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)
from insurance_intelligence.response.registry import (
    ResponseFormatRegistry,
    build_format_definition,
)
from insurance_intelligence.response.service import assemble_response


def _finding():
    return build_finding(
        finding_id="finding-1",
        requirement_id="requirement-1",
        finding_type="DOCUMENTED_FACT",
        subject="star_health:star_comprehensive",
        predicate="documents",
        object_or_effect="The waiting period duration is 36 MONTHS.",
        condition=None,
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="DIRECT_FACT",
        rule_id="documented_fact_v1",
        rule_version="1.0",
        evidence_ids=("product-evidence-1",),
        limitations=(),
        confidence=1.0,
    )


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-1",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("product-evidence-1",),
        limitation_ids=(),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED",
        basis="Supported by governed product evidence.",
        approved_evidence_ids=("product-evidence-1",),
        confidence=1.0,
    )
    return build_decision_output(
        request_id="request-1",
        decision_id="decision-1",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=1.0,
    )


def _education() -> EducationPublicationRecord:
    return EducationPublicationRecord(
        contract_version="1.0",
        publication_id="education-pub-waiting-period",
        publication_status=EDUCATION_PUBLICATION_STATUS,
        allowed_uses=(CUSTOMER_EDUCATION,),
        concept_id="waiting_period",
        canonical_name="Waiting Period",
        definition=(
            "A waiting period is a policy-defined period during which a specified "
            "coverage restriction applies."
        ),
        plain_language_explanation=(
            "Some parts of a health policy do not become available immediately."
        ),
        practical_implication=(
            "The specific clause determines what is restricted and for how long."
        ),
        examples=(
            EducationExample(
                scenario="A policy has a waiting-period clause for a specified condition.",
                result="That restriction can still apply during the applicable period.",
                boundary=(
                    "Illustrative only. This does not decide claim approval or payment."
                ),
            ),
        ),
        limitations=("This is generic education, not a product-specific duration.",),
        product_specific_boundary=(
            "Product-specific duration and mechanics must come from governed product knowledge."
        ),
        customer_document_boundary=(
            "Customer-specific dates and selections must come from applicable documents."
        ),
        evidence_references=("education-evidence-1",),
        source_asset_id="meaning-waiting-period",
        source_asset_digest="a" * 64,
        source_governed_record_id="gconcept-waiting-period",
        source_knowledge_version="1.0",
        review_decision_id="review-waiting-period",
        publication_authority="PolicyScna education publication authority",
        publication_receipt_id="education_receipt_1234567890abcdef1234",
    )


def _styles():
    return ExplanationStyleRegistry((
        build_style_definition(
            style_id="customer-simple-v1",
            style_version="1.0",
            audience="CUSTOMER",
            reading_level="SIMPLE",
            explanation_modes=("PLAIN_LANGUAGE",),
        ),
    ))


def _responses():
    return ResponseFormatRegistry((
        build_format_definition(
            format_id="customer-education-answer-v1",
            format_version="1.0",
            response_format="STANDARD",
            audiences=("CUSTOMER",),
            response_statuses=("ANSWER",),
            section_order=(
                "DIRECT_ANSWER",
                "EDUCATION",
                "EXPLANATION",
                "CONDITION",
                "EXAMPLE",
                "IMPACT",
                "LIMITATION",
                "EVIDENCE",
            ),
            allowed_section_types=(
                "DIRECT_ANSWER",
                "EDUCATION",
                "EXPLANATION",
                "CONDITION",
                "EXAMPLE",
                "IMPACT",
                "LIMITATION",
                "EVIDENCE",
            ),
            direct_answer_policy="REQUIRED",
            evidence_policy="WHEN_AVAILABLE",
            limitation_policy="REQUIRED_WHEN_PRESENT",
            assumption_policy="WHEN_PRESENT",
            clarification_policy="FORBIDDEN",
        ),
    ))


def test_admitted_education_enriches_explanation_without_becoming_product_evidence() -> None:
    education = _education()
    explanation_input = build_explanation_input(
        request_id="request-1",
        decision_output=_decision(),
        education_publications=(education,),
    )
    explanation = generate_explanation(
        explanation_input=explanation_input,
        findings_by_id={"finding-1": _finding()},
        style_registry=_styles(),
    )

    education_sections = tuple(
        section
        for section in explanation.sections
        if section.section_type in {"EDUCATION", "EXAMPLE"}
    )
    assert {section.section_type for section in education_sections} == {
        "EDUCATION",
        "EXAMPLE",
    }
    assert all(
        section.education_publication_ids == (education.publication_id,)
        for section in education_sections
    )
    assert all(not section.approved_finding_ids for section in education_sections)
    assert all(not section.evidence_ids for section in education_sections)

    response = assemble_response(
        build_response_input(
            request_id="request-1",
            decision_output=_decision(),
            explanation_output=explanation,
            response_format="STANDARD",
        ),
        _responses(),
    )

    assert response.direct_answer == "The waiting period duration is 36 MONTHS."
    assert response.sections[0].section_type == "EDUCATION"
    assert response.sections[1].section_type == "EXPLANATION"
    assert any(section.section_type == "EXAMPLE" for section in response.sections)
    assert {ref.source_id for ref in response.evidence_references} == {
        "product-evidence-1"
    }


def test_tampered_education_text_fails_fidelity() -> None:
    education = _education()
    explanation_input = build_explanation_input(
        request_id="request-1",
        decision_output=_decision(),
        education_publications=(education,),
    )
    finding = _finding()
    explanation = generate_explanation(
        explanation_input=explanation_input,
        findings_by_id={"finding-1": finding},
        style_registry=_styles(),
    )

    tampered = tuple(
        replace(section, text=section.text + " Invented customer meaning.")
        if section.section_type == "EDUCATION"
        else section
        for section in explanation.sections
    )
    validation = validate_explanation_fidelity(
        explanation_input=explanation_input,
        sections=tampered,
        findings_by_id={"finding-1": finding},
        terminology_substitutions=explanation.terminology_substitutions,
    )

    assert validation.fidelity_status == "FAILED"
    assert any(
        check.check_type == "EDUCATION_PUBLICATION_FIDELITY"
        and check.status == "FAILED"
        for check in validation.checks
    )



def test_customer_education_renders_reviewed_plain_language_before_formal_definition() -> None:
    education = _education()

    sections = render_education_sections(
        request_id="request-plain-first",
        publications=(education,),
    )
    meaning = next(section for section in sections if section.section_type == "EDUCATION")

    assert education.plain_language_explanation in meaning.text
    assert education.practical_implication in meaning.text
    assert education.definition not in meaning.text
