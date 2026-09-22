from __future__ import annotations

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
from insurance_intelligence.contracts.explanation import build_input
from insurance_intelligence.contracts.reasoning import build_finding
from insurance_intelligence.explanation.generator import generate_explanation
from insurance_intelligence.explanation.registry import (
    ExplanationStyleRegistry,
    build_style_definition,
)


def _finding():
    return build_finding(
        finding_id="finding-1",
        requirement_id="requirement-1",
        finding_type="DOCUMENTED_FACT",
        subject="star_comprehensive",
        predicate="documents",
        object_or_effect="The waiting period duration is 36 MONTHS.",
        condition="",
        scope="star_health:star_comprehensive",
        finding_status="SUPPORTED",
        derivation_type="DIRECT_FACT",
        rule_id="published_documented_fact_v1",
        rule_version="1.0",
        evidence_ids=("product-evidence-1",),
        limitations=(),
        confidence=0.98,
    )


def _decision():
    packet = build_approved_response_packet(
        packet_id="packet-education-enrichment",
        approved_finding_ids=("finding-1",),
        approved_evidence_ids=("product-evidence-1",),
        limitation_ids=(),
        prohibited_operations=("RECOMMEND",),
    )
    disposition = build_finding_disposition(
        finding_id="finding-1",
        disposition="APPROVED",
        basis="Supported by governed product evidence.",
        approved_evidence_ids=("product-evidence-1",),
        confidence=0.98,
    )
    return build_decision_output(
        request_id="request-education-enrichment",
        decision_id="decision-education-enrichment",
        decision="APPROVED",
        finding_dispositions=(disposition,),
        response_packet=packet,
        confidence=0.95,
    )


def _education() -> EducationPublicationRecord:
    return EducationPublicationRecord(
        contract_version="1.0",
        publication_id="education-publication-waiting-period-v1",
        publication_status=EDUCATION_PUBLICATION_STATUS,
        allowed_uses=(CUSTOMER_EDUCATION,),
        concept_id="waiting_period",
        canonical_name="Waiting Period",
        definition="A waiting period is a policy-defined period.",
        plain_language_explanation=(
            "Some parts of a health policy do not become available immediately."
        ),
        practical_implication=(
            "The applicable policy rule must be checked before applying this concept "
            "to a specific customer situation."
        ),
        examples=(
            EducationExample(
                scenario="A policy contains a waiting-period clause.",
                result="That restriction can apply during the governed period.",
                boundary=(
                    "Illustrative only. This does not determine claim approval or payment."
                ),
            ),
        ),
        limitations=("Generic education only.",),
        product_specific_boundary=(
            "Product duration, scope and exceptions require governed product evidence."
        ),
        customer_document_boundary=(
            "Customer dates and selections require applicable customer documents."
        ),
        evidence_references=("education-evidence-1",),
        source_asset_id="meaning-waiting-period-v1",
        source_asset_digest="a" * 64,
        source_governed_record_id="gconcept-waiting-period-v1",
        source_knowledge_version="1.0",
        review_decision_id="review-waiting-period-v1",
        publication_authority="PolicyScna education publication gate",
        publication_receipt_id="education-receipt-waiting-period-v1",
    )


def _styles():
    return ExplanationStyleRegistry(
        (
            build_style_definition(
                style_id="customer-simple",
                style_version="1.0",
                audience="CUSTOMER",
                reading_level="SIMPLE",
                explanation_modes=("PLAIN_LANGUAGE",),
                max_section_words=120,
                priority=10,
            ),
        )
    )


def test_published_education_enriches_explanation_without_entering_decision_authority() -> None:
    decision = _decision()
    education = _education()

    item = build_input(
        request_id="request-education-enrichment",
        decision_output=decision,
        education_publications=(education,),
        communication_context={"domain_scope": "HEALTH"},
    )
    result = generate_explanation(
        explanation_input=item,
        findings_by_id={"finding-1": _finding()},
        style_registry=_styles(),
    )

    education_sections = tuple(
        section for section in result.sections if section.education_references
    )
    assert {section.section_type for section in education_sections} == {
        "MEANING",
        "IMPACT",
        "EXAMPLE",
    }
    assert all(not section.approved_finding_ids for section in education_sections)
    assert all(not section.evidence_ids for section in education_sections)
    assert all(
        section.education_references[0].publication_id == education.publication_id
        for section in education_sections
    )
    assert all(
        section.education_references[0].publication_receipt_id
        == education.publication_receipt_id
        for section in education_sections
    )

    text = " ".join(section.text for section in education_sections)
    assert education.definition in text
    assert education.plain_language_explanation in text
    assert education.practical_implication in text
    assert education.examples[0].scenario in text
    assert education.examples[0].result in text
    assert education.examples[0].boundary in text

    assert result.fidelity_status == "VERIFIED"
    assert any(
        check.check_type == "EDUCATION_PUBLICATION_LINEAGE"
        and check.status == "PASSED"
        for check in result.fidelity_checks
    )
    assert any(
        check.check_type == "EDUCATION_CONTENT_FIDELITY"
        and check.status == "PASSED"
        for check in result.fidelity_checks
    )

    assert item.decision_output is decision
    assert decision.response_packet is not None
    assert decision.response_packet.approved_finding_ids == ("finding-1",)
    assert decision.response_packet.approved_evidence_ids == ("product-evidence-1",)
    assert education.publication_id not in decision.response_packet.approved_evidence_ids


def test_no_education_publication_preserves_existing_explanation_path() -> None:
    item = build_input(
        request_id="request-education-enrichment",
        decision_output=_decision(),
    )
    result = generate_explanation(
        explanation_input=item,
        findings_by_id={"finding-1": _finding()},
        style_registry=_styles(),
    )

    assert all(not section.education_references for section in result.sections)
    assert not any(section.section_type == "EXAMPLE" for section in result.sections)
    assert result.fidelity_status == "VERIFIED"
